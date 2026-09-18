import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { equipmentApi } from '../../api/equipment.js';
import DataTable from '../../components/DataTable.jsx';
import DetailList from '../../components/DetailList.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { formatDate, formatDateTime, maintenanceDueState } from '../../utils/format.js';
import EquipmentFormModal from './EquipmentFormModal.jsx';
import MaintenanceFormModal from './MaintenanceFormModal.jsx';
import ScrapFormModal from './ScrapFormModal.jsx';

const TABS = [
  { key: 'profile', label: '基础档案' },
  { key: 'maintenances', label: '保养记录' },
  { key: 'scraps', label: '报废记录' },
];

export default function EquipmentDetailPage() {
  const { equipmentId } = useParams();
  const { dictionaries } = useDictionaries();
  const [tab, setTab] = useState('profile');
  const [showForm, setShowForm] = useState(false);
  const [showMaintenance, setShowMaintenance] = useState(false);
  const [showScrap, setShowScrap] = useState(false);

  const { data: equipment, loading, error, reload } = useAsync(
    () => equipmentApi.detail(equipmentId),
    [equipmentId],
  );

  const inUse = equipment?.status !== '已报废';
  const due = equipment
    ? maintenanceDueState(
        equipment.next_maintenance_at,
        equipment.status,
        dictionaries?.maintenance_remind_days ?? 7,
      )
    : null;

  return (
    <>
      <PageHeader
        title={equipment ? `${equipment.name}（${equipment.code}）` : '设备详情'}
        description={
          equipment
            ? `${equipment.category} · 使用人 ${equipment.assignee || '未指定'} · ${equipment.location || '存放地点未登记'}`
            : '加载中…'
        }
        actions={
          <>
            <Link className="btn" to="/equipment">
              返回列表
            </Link>
            <button
              type="button"
              className="btn"
              disabled={!inUse}
              onClick={() => setShowScrap(true)}
            >
              报废登记
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!inUse}
              onClick={() => setShowMaintenance(true)}
            >
              登记保养
            </button>
            <button type="button" className="btn" onClick={() => setShowForm(true)}>
              编辑档案
            </button>
          </>
        }
      />
      <div className="content">
        {error ? <div className="alert alert-error">{error.message}</div> : null}
        {loading && !equipment ? <div className="loading-block">加载中…</div> : null}

        {equipment ? (
          <>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="label">配置数量</div>
                <div className="value">
                  {equipment.quantity}
                  <span className="unit">{equipment.unit}</span>
                </div>
                <div className="foot">可用 {equipment.available_quantity} {equipment.unit}</div>
              </div>
              <div className={`stat-card${due?.tone === 'tag-danger' ? ' is-danger' : due ? ' is-warning' : ''}`}>
                <div className="label">下次保养</div>
                <div className="value" style={{ fontSize: 20 }}>
                  {equipment.status === '已报废' ? '—' : formatDate(equipment.next_maintenance_at)}
                </div>
                <div className="foot">
                  周期 {equipment.maintenance_cycle}
                  {due ? ` · ${due.label}` : ''}
                </div>
              </div>
              <div className="stat-card is-info">
                <div className="label">累计保养</div>
                <div className="value">
                  {equipment.maintenance_records.length}
                  <span className="unit">次</span>
                </div>
                <div className="foot">
                  最近保养：{formatDateTime(equipment.last_maintained_at)}
                </div>
              </div>
              <div className={`stat-card${equipment.scrapped_quantity ? ' is-warning' : ''}`}>
                <div className="label">累计报废</div>
                <div className="value">
                  {equipment.scrapped_quantity}
                  <span className="unit">{equipment.unit}</span>
                </div>
                <div className="foot">
                  <StatusTag status={equipment.status} />
                </div>
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
                    { label: '名称', value: equipment.name },
                    { label: '分类', value: equipment.category },
                    {
                      label: '数量',
                      value: `配置 ${equipment.quantity} ${equipment.unit} · 可用 ${equipment.available_quantity} ${equipment.unit} · 已报废 ${equipment.scrapped_quantity} ${equipment.unit}`,
                    },
                    { label: '使用人', value: equipment.assignee || '未指定' },
                    { label: '存放地点', value: equipment.location || '未登记' },
                    { label: '保养周期', value: equipment.maintenance_cycle },
                    { label: '最近保养时间', value: formatDateTime(equipment.last_maintained_at) },
                    {
                      label: '下次保养日期',
                      value:
                        equipment.status === '已报废'
                          ? '已报废，不再提醒'
                          : formatDate(equipment.next_maintenance_at),
                    },
                    { label: '使用状态', value: <StatusTag status={equipment.status} /> },
                    { label: '备注', value: equipment.remark || '无' },
                    { label: '建档时间', value: formatDateTime(equipment.created_at) },
                  ]}
                />
              </section>
            ) : null}

            {tab === 'maintenances' ? (
              <section className="card">
                <div className="card-title">
                  <h3>保养记录</h3>
                  <span className="hint">共 {equipment.maintenance_records.length} 条</span>
                </div>
                <DataTable
                  rows={equipment.maintenance_records}
                  emptyText="暂无保养记录"
                  columns={[
                    {
                      key: 'maintained_at',
                      title: '保养时间',
                      render: (row) => formatDateTime(row.maintained_at),
                    },
                    { key: 'operator', title: '保养人' },
                    { key: 'content', title: '保养内容', wrap: true },
                    {
                      key: 'replaced_parts',
                      title: '更换部件',
                      wrap: true,
                      render: (row) => row.replaced_parts || '-',
                    },
                    {
                      key: 'cost',
                      title: '费用(元)',
                      render: (row) => (row.cost != null ? row.cost.toFixed(2) : '-'),
                    },
                    { key: 'remark', title: '备注', wrap: true, render: (row) => row.remark || '-' },
                  ]}
                />
              </section>
            ) : null}

            {tab === 'scraps' ? (
              <section className="card">
                <div className="card-title">
                  <h3>报废记录</h3>
                  <span className="hint">共 {equipment.scrap_records.length} 条</span>
                </div>
                <DataTable
                  rows={equipment.scrap_records}
                  emptyText="暂无报废记录"
                  columns={[
                    {
                      key: 'scrapped_at',
                      title: '报废时间',
                      render: (row) => formatDateTime(row.scrapped_at),
                    },
                    {
                      key: 'quantity',
                      title: '数量',
                      render: (row) => `${row.quantity} ${equipment.unit}`,
                    },
                    { key: 'reason', title: '报废原因', wrap: true },
                    { key: 'disposal_method', title: '处置方式' },
                    { key: 'operator', title: '经办人' },
                    { key: 'remark', title: '备注', wrap: true, render: (row) => row.remark || '-' },
                  ]}
                />
              </section>
            ) : null}
          </>
        ) : null}
      </div>

      {showForm && equipment ? (
        <EquipmentFormModal equipment={equipment} onClose={() => setShowForm(false)} onSaved={reload} />
      ) : null}
      {showMaintenance && equipment ? (
        <MaintenanceFormModal
          equipment={equipment}
          onClose={() => setShowMaintenance(false)}
          onSaved={reload}
        />
      ) : null}
      {showScrap && equipment ? (
        <ScrapFormModal equipment={equipment} onClose={() => setShowScrap(false)} onSaved={reload} />
      ) : null}
    </>
  );
}
