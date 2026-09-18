import { useState } from 'react';
import { Link } from 'react-router-dom';

import { equipmentApi } from '../../api/equipment.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { MaintenanceDueTag, StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDate } from '../../utils/format.js';
import EquipmentFormModal from './EquipmentFormModal.jsx';

const DEFAULT_FILTERS = { keyword: '', category: '', status: '', due: '' };
const DUE_OPTIONS = ['已逾期', '临近到期', '正常'];

export default function EquipmentListPage() {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const list = useListQuery((params) => equipmentApi.list(params), DEFAULT_FILTERS, 10);
  const reminders = useAsync(() => equipmentApi.reminders(), []);

  const remove = async (row) => {
    if (!window.confirm(`确认销毁/删除设备「${row.name}」的台账？`)) return;
    try {
      await equipmentApi.remove(row.id);
      toast.success('删除成功');
      list.reload();
      reminders.reload();
    } catch (err) {
      if (err.status === 409 && window.confirm(`${err.message}\n\n是否连同保养记录一并删除？`)) {
        await equipmentApi.remove(row.id, { force: true });
        toast.success('已级联删除');
        list.reload();
        reminders.reload();
        return;
      }
      toast.error(err.message);
    }
  };

  const overdueCount = reminders.data?.overdue?.length ?? 0;
  const upcomingCount = reminders.data?.upcoming?.length ?? 0;

  return (
    <>
      <PageHeader
        title="工具与设备台账"
        description="保洁工具设备的登记、保养周期提醒与报废处置管理"
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setEditing(null);
              setShowForm(true);
            }}
          >
            + 新增设备
          </button>
        }
      />
      <div className="content">
        {overdueCount + upcomingCount > 0 ? (
          <div className={`alert ${overdueCount ? 'alert-error' : 'alert-info'}`}>
            保养提醒：{overdueCount ? `${overdueCount} 台设备保养已逾期` : ''}
            {overdueCount && upcomingCount ? '，' : ''}
            {upcomingCount ? `${upcomingCount} 台设备临近保养到期` : ''}
            <button
              type="button"
              className="btn-link"
              style={{ marginLeft: 12 }}
              onClick={() => list.updateFilter('due', overdueCount ? '已逾期' : '临近到期')}
            >
              查看 →
            </button>
          </div>
        ) : null}

        <section className="card">
          <div className="filter-bar">
            <Field label="关键字" full>
              <input
                value={list.filters.keyword}
                placeholder="名称 / 编号 / 使用人"
                onChange={(event) => list.updateFilter('keyword', event.target.value)}
              />
            </Field>
            <Field label="设备分类">
              <select
                value={list.filters.category}
                onChange={(event) => list.updateFilter('category', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.equipment_category || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="设备状态">
              <select
                value={list.filters.status}
                onChange={(event) => list.updateFilter('status', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.equipment_status || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="保养到期">
              <select
                value={list.filters.due}
                onChange={(event) => list.updateFilter('due', event.target.value)}
              >
                <option value="">全部</option>
                {DUE_OPTIONS.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <button type="button" className="btn" onClick={list.resetFilters}>
              重置
            </button>
          </div>
        </section>

        <section className="card">
          <DataTable
            loading={list.loading}
            error={list.error}
            rows={list.items}
            emptyText="暂无设备台账"
            columns={[
              { key: 'code', title: '编号' },
              {
                key: 'name',
                title: '设备名称',
                render: (row) => <Link to={`/equipment/${row.id}`}>{row.name}</Link>,
              },
              { key: 'category', title: '分类' },
              {
                key: 'quantity',
                title: '配置数量',
                render: (row) => `${row.quantity} ${row.unit}`,
              },
              { key: 'custodian', title: '使用人', render: (row) => row.custodian || '-' },
              {
                key: 'maintenance_cycle_days',
                title: '保养周期',
                render: (row) => `${row.maintenance_cycle_days} 天`,
              },
              {
                key: 'next_maintenance_date',
                title: '下次保养',
                render: (row) => (
                  <div className="inline">
                    <span>{formatDate(row.next_maintenance_date)}</span>
                    <MaintenanceDueTag due={row.maintenance_due} />
                  </div>
                ),
              },
              { key: 'maintenance_count', title: '保养次数' },
              { key: 'status', title: '状态', render: (row) => <StatusTag status={row.status} /> },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="inline">
                    <Link className="btn-link" to={`/equipment/${row.id}`}>
                      详情
                    </Link>
                    <button
                      type="button"
                      className="btn-link"
                      onClick={() => {
                        setEditing(row);
                        setShowForm(true);
                      }}
                    >
                      编辑
                    </button>
                    <button type="button" className="btn-link danger" onClick={() => remove(row)}>
                      删除
                    </button>
                  </div>
                ),
              },
            ]}
          />
          <Pagination meta={list.meta} onPageChange={list.setPage} />
        </section>
      </div>

      {showForm ? (
        <EquipmentFormModal
          equipment={editing}
          onClose={() => setShowForm(false)}
          onSaved={() => {
            list.reload();
            reminders.reload();
          }}
        />
      ) : null}
    </>
  );
}
