import { useState } from 'react';
import { Link } from 'react-router-dom';

import { equipmentApi } from '../../api/equipment.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDate, maintenanceDueState } from '../../utils/format.js';
import EquipmentFormModal from './EquipmentFormModal.jsx';
import MaintenanceFormModal from './MaintenanceFormModal.jsx';
import ScrapFormModal from './ScrapFormModal.jsx';

const DEFAULT_FILTERS = { keyword: '', category: '', status: '', maintenance_cycle: '', due: '' };

export default function EquipmentListPage() {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [maintaining, setMaintaining] = useState(null);
  const [scrapping, setScrapping] = useState(null);

  const list = useListQuery((params) => equipmentApi.list(params), DEFAULT_FILTERS, 10);
  const reminders = useAsync(() => equipmentApi.reminders(), []);

  const reloadAll = () => {
    list.reload();
    reminders.reload();
  };

  const remove = async (row) => {
    if (!window.confirm(`确认删除设备「${row.name}」（${row.code}）？`)) return;
    try {
      await equipmentApi.remove(row.id);
      toast.success('删除成功');
      reloadAll();
    } catch (err) {
      if (err.status === 409 && window.confirm(`${err.message}\n\n是否连同保养与报废记录一并删除？`)) {
        await equipmentApi.remove(row.id, { force: true });
        toast.success('已级联删除');
        reloadAll();
        return;
      }
      toast.error(err.message);
    }
  };

  const overdueCount = reminders.data?.overdue?.length ?? 0;
  const upcomingCount = reminders.data?.upcoming?.length ?? 0;
  const remindDays = dictionaries?.maintenance_remind_days ?? 7;

  return (
    <>
      <PageHeader
        title="工具设备台账"
        description="保洁工具与设备的登记、周期保养与报废处置"
        actions={
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setEditing(null);
              setShowForm(true);
            }}
          >
            + 登记设备
          </button>
        }
      />
      <div className="content">
        {overdueCount + upcomingCount > 0 ? (
          <div className={`alert ${overdueCount ? 'alert-error' : 'alert-info'}`}>
            保养提醒：{overdueCount ? ` ${overdueCount} 台设备保养已超期` : ''}
            {overdueCount && upcomingCount ? '，' : ''}
            {upcomingCount ? ` ${upcomingCount} 台设备 ${remindDays} 日内到期` : ''}。
            <button
              type="button"
              className="btn-link"
              onClick={() => list.updateFilter('due', 'overdue')}
            >
              查看超期
            </button>
            <button
              type="button"
              className="btn-link"
              onClick={() => list.updateFilter('due', 'upcoming')}
            >
              查看即将到期
            </button>
          </div>
        ) : null}

        <section className="card">
          <div className="filter-bar">
            <Field label="关键字" full>
              <input
                value={list.filters.keyword}
                placeholder="名称 / 编号 / 使用人 / 存放地点"
                onChange={(event) => list.updateFilter('keyword', event.target.value)}
              />
            </Field>
            <Field label="分类">
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
            <Field label="状态">
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
            <Field label="保养周期">
              <select
                value={list.filters.maintenance_cycle}
                onChange={(event) => list.updateFilter('maintenance_cycle', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.maintenance_cycle || []).map((item) => (
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
                <option value="overdue">已超期</option>
                <option value="upcoming">{remindDays} 日内到期</option>
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
            emptyText="暂无工具设备档案"
            columns={[
              { key: 'code', title: '编号' },
              {
                key: 'name',
                title: '名称',
                render: (row) => <Link to={`/equipment/${row.id}`}>{row.name}</Link>,
              },
              { key: 'category', title: '分类' },
              {
                key: 'quantity',
                title: '数量(可用/配置)',
                render: (row) => `${row.available_quantity}/${row.quantity} ${row.unit}`,
              },
              { key: 'assignee', title: '使用人', render: (row) => row.assignee || '-' },
              { key: 'maintenance_cycle', title: '保养周期' },
              {
                key: 'last_maintained_at',
                title: '最近保养',
                render: (row) => formatDate(row.last_maintained_at),
              },
              {
                key: 'next_maintenance_at',
                title: '下次保养',
                render: (row) => {
                  const due = maintenanceDueState(row.next_maintenance_at, row.status, remindDays);
                  return (
                    <div className="inline">
                      {formatDate(row.next_maintenance_at)}
                      {due ? <span className={`tag ${due.tone}`}>{due.label}</span> : null}
                    </div>
                  );
                },
              },
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
                      disabled={row.status === '已报废'}
                      onClick={() => setMaintaining(row)}
                    >
                      保养
                    </button>
                    <button
                      type="button"
                      className="btn-link"
                      disabled={row.status === '已报废'}
                      onClick={() => setScrapping(row)}
                    >
                      报废
                    </button>
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
          onSaved={reloadAll}
        />
      ) : null}
      {maintaining ? (
        <MaintenanceFormModal
          equipment={maintaining}
          onClose={() => setMaintaining(null)}
          onSaved={reloadAll}
        />
      ) : null}
      {scrapping ? (
        <ScrapFormModal
          equipment={scrapping}
          onClose={() => setScrapping(null)}
          onSaved={reloadAll}
        />
      ) : null}
    </>
  );
}
