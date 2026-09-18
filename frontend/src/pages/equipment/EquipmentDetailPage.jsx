import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { equipmentApi } from '../../api/equipment.js';
import DataTable from '../../components/DataTable.jsx';
import DetailList from '../../components/DetailList.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import { MaintenanceDueTag, StatusTag } from '../../components/Tags.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatDate, formatDateTime, formatMaintenanceDays } from '../../utils/format.js';
import EquipmentFormModal from './EquipmentFormModal.jsx';
import MaintenanceFormModal from './MaintenanceFormModal.jsx';
import ScrapModal from './ScrapModal.jsx';

const TABS = [
  { key: 'profile', label: '基础档案' },
  { key: 'maintenance', label: '保养记录' },
];

export default function EquipmentDetailPage() {
  const { equipmentId } = useParams();
  const [tab, setTab] = useState('profile');
  const [showEdit, setShowEdit] = useState(false);
  const [showMaintenance, setShowMaintenance] = useState(false);
  const [showScrap, setShowScrap] = useState(false);

  const { data: equipment, loading, error, reload } = useAsync(
    () => equipmentApi.detail(equipmentId),
    [equipmentId],
  );

  const scrapped = equipment?.status === '已报废';

  return (
    <>
      <PageHeader
        title={equipment ? `${equipment.name}（${equipment.code}）` : '设备详情'}
        description={
          equipment
            ? `${equipment.category} · 使用人：${equipment.custodian || '未指定'}`
            : '加载中…'
        }
        actions={
          <>
            <Link className="btn" to="/equipment">
              返回列表
            </Link>
            {equipment && !scrapped ? (
              <>
                <button type="button" className="btn" onClick={() => setShowEdit(true)}>
                  编辑档案
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setShowMaintenance(true)}
                >
                  登记保养
                </button>
                <button type="button" className="btn btn-danger" onClick={() => setShowScrap(true)}>
                  报废登记
                </button>
              </>
            ) : null}
          </>
        }
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !equipment ? <div className="loading-block">加载中…</div> : null}

        {equipment ? (
          <>
            {scrapped ? (
              <div className="alert alert-error">
                该设备已于 {formatDateTime(equipment.scrapped_at)} 报废：{equipment.scrap_reason}
                （处置方式：{equipment.disposal_method}
                {equipment.scrap_note ? `，${equipment.scrap_note}` : ''}）
              </div>
            ) : null}

            <div className="stat-grid">
              <div className={`stat-card${equipment.maintenance_due === '已逾期' ? ' is-danger' : equipment.maintenance_due === '临近到期' ? ' is-warning' : ''}`}>
                <div className="label">保养状态</div>
                <div className="value" style={{ fontSize: 22 }}>
                  {scrapped ? '已报废' : equipment.maintenance_due || '未排期'}
                </div>
                <div className="foot">
                  {scrapped
                    ? '不再参与保养提醒'
                    : `距下次保养：${formatMaintenanceDays(equipment.days_to_maintenance)}`}
                </div>
              </div>
              <div className="stat-card is-info">
                <div className="label">下次保养日期</div>
                <div className="value" style={{ fontSize: 22 }}>
                  {formatDate(equipment.next_maintenance_date)}
                </div>
                <div className="foot">
                  上次保养：{formatDateTime(equipment.last_maintained_at)}
                </div>
              </div>
              <div className="stat-card">
                <div className="label">保养周期</div>
                <div className="value">
                  {equipment.maintenance_cycle_days}
                  <span className="unit">天</span>
                </div>
                <div className="foot">按周期自动生成保养提醒</div>
              </div>
              <div className="stat-card">
                <div className="label">累计保养</div>
                <div className="value">
                  {equipment.maintenance_count}
                  <span className="unit">次</span>
                </div>
                <div className="foot">含更换部件记录</div>
              </div>
            </div>

            <div className="inline">
              {TABS.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={`btn btn-sm${tab === item.key ? ' btn-primary' : ''}`}
                  onClick={() => setTab(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {tab === 'profile' ? (
              <section className="card">
                <div className="card-title">
                  <h3>基础档案</h3>
                </div>
                <DetailList
                  items={[
                    { label: '设备编号', value: equipment.code },
                    { label: '设备名称', value: equipment.name },
                    { label: '设备分类', value: equipment.category },
                    { label: '配置数量', value: `${equipment.quantity} ${equipment.unit}` },
                    { label: '使用人', value: equipment.custodian || '未指定' },
                    {
                      label: '配置地点',
                      value: equipment.restroom ? (
                        <Link to={`/restrooms/${equipment.restroom.id}`}>
                          {equipment.restroom.name}
                        </Link>
                      ) : (
                        '公共库房'
                      ),
                    },
                    { label: '设备状态', value: <StatusTag status={equipment.status} /> },
                    {
                      label: '保养到期',
                      value: scrapped ? '已报废' : <MaintenanceDueTag due={equipment.maintenance_due} />,
                    },
                    { label: '购置日期', value: formatDate(equipment.purchase_date) },
                    { label: '报废时间', value: formatDateTime(equipment.scrapped_at) },
                    { label: '报废原因', value: equipment.scrap_reason || '-' },
                    { label: '处置方式', value: equipment.disposal_method || '-' },
                    { label: '处置说明', value: equipment.scrap_note || '-' },
                    { label: '备注', value: equipment.remark || '无' },
                    { label: '建档时间', value: formatDateTime(equipment.created_at) },
                  ]}
                />
              </section>
            ) : null}

            {tab === 'maintenance' ? (
              <section className="card">
                <div className="card-title">
                  <h3>保养记录</h3>
                  <span className="hint">共 {equipment.records?.length ?? 0} 条</span>
                </div>
                <DataTable
                  rows={equipment.records || []}
                  emptyText="暂无保养记录"
                  columns={[
                    {
                      key: 'maintained_at',
                      title: '保养时间',
                      render: (row) => formatDateTime(row.maintained_at),
                    },
                    { key: 'content', title: '保养内容', wrap: true },
                    {
                      key: 'replaced_parts',
                      title: '更换部件',
                      wrap: true,
                      render: (row) => row.replaced_parts || '-',
                    },
                    { key: 'operator', title: '保养人', render: (row) => row.operator || '-' },
                    { key: 'remark', title: '备注', wrap: true, render: (row) => row.remark || '-' },
                  ]}
                />
              </section>
            ) : null}
          </>
        ) : null}
      </div>

      {showEdit && equipment ? (
        <EquipmentFormModal
          equipment={equipment}
          onClose={() => setShowEdit(false)}
          onSaved={reload}
        />
      ) : null}
      {showMaintenance && equipment ? (
        <MaintenanceFormModal
          equipment={equipment}
          onClose={() => setShowMaintenance(false)}
          onSaved={reload}
        />
      ) : null}
      {showScrap && equipment ? (
        <ScrapModal equipment={equipment} onClose={() => setShowScrap(false)} onSaved={reload} />
      ) : null}
    </>
  );
}
