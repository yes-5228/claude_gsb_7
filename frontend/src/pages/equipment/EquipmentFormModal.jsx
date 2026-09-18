import { useState } from 'react';

import { equipmentApi } from '../../api/equipment.js';
import { metaApi } from '../../api/meta.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';

const EMPTY = {
  name: '',
  category: '保洁工具',
  quantity: 1,
  unit: '台',
  custodian: '',
  restroom_id: '',
  maintenance_cycle_days: 30,
  purchase_date: '',
  remark: '',
};

export default function EquipmentFormModal({ equipment, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const isEdit = Boolean(equipment?.id);
  const [form, setForm] = useState(() => ({
    ...EMPTY,
    ...(equipment ?? {}),
    restroom_id: equipment?.restroom_id ?? '',
    purchase_date: equipment?.purchase_date ?? '',
    remark: equipment?.remark ?? '',
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const { data: restroomOptions } = useAsync(() => metaApi.restroomOptions(), []);

  const setValue = (key) => (event) => {
    const target = event.target;
    const value = target.type === 'number' ? Number(target.value) : target.value;
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setError('设备名称为必填项');
      return;
    }
    if (!Number.isInteger(Number(form.quantity)) || Number(form.quantity) < 1) {
      setError('配置数量需为不小于 1 的整数');
      return;
    }
    if (!Number.isInteger(Number(form.maintenance_cycle_days)) || Number(form.maintenance_cycle_days) < 1) {
      setError('保养周期需为不小于 1 的整数天数');
      return;
    }
    setSaving(true);
    setError(null);
    const payload = {
      name: form.name.trim(),
      category: form.category,
      quantity: Number(form.quantity),
      unit: form.unit.trim() || '台',
      custodian: form.custodian.trim(),
      restroom_id: form.restroom_id ? Number(form.restroom_id) : null,
      maintenance_cycle_days: Number(form.maintenance_cycle_days),
      purchase_date: form.purchase_date || null,
      remark: form.remark?.trim() || null,
    };
    try {
      if (isEdit) {
        await equipmentApi.update(equipment.id, { ...payload, status: form.status });
        toast.success('设备信息已更新');
      } else {
        await equipmentApi.create(payload);
        toast.success('设备已登记');
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={isEdit ? `编辑设备 - ${equipment.code}` : '新增设备'}
      onClose={onClose}
      width={760}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="equipment-form" className="btn btn-primary" disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="equipment-form" className="form-grid" onSubmit={submit}>
        <Field label="设备名称 *">
          <input value={form.name} onChange={setValue('name')} placeholder="如：驾驶式洗地机" />
        </Field>
        <Field label="设备分类">
          <select value={form.category} onChange={setValue('category')}>
            {(dictionaries?.equipment_category || ['保洁工具', '机械设备', '车辆设备', '电器设备', '其他']).map(
              (item) => (
                <option key={item}>{item}</option>
              ),
            )}
          </select>
        </Field>
        <Field label="配置数量 *">
          <input type="number" min="1" step="1" value={form.quantity} onChange={setValue('quantity')} />
        </Field>
        <Field label="计量单位">
          <input value={form.unit} onChange={setValue('unit')} placeholder="台 / 把 / 套 / 辆" />
        </Field>
        <Field label="使用人">
          <input value={form.custodian} onChange={setValue('custodian')} placeholder="保管/使用责任人" />
        </Field>
        <Field label="配置地点">
          <select value={form.restroom_id} onChange={setValue('restroom_id')}>
            <option value="">未指定（公共库房）</option>
            {(restroomOptions || []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}（{item.district}）
              </option>
            ))}
          </select>
        </Field>
        <Field label="保养周期（天）*" hint="按周期自动生成保养提醒">
          <input
            type="number"
            min="1"
            step="1"
            value={form.maintenance_cycle_days}
            onChange={setValue('maintenance_cycle_days')}
          />
        </Field>
        <Field label="购置日期">
          <input type="date" value={form.purchase_date || ''} onChange={setValue('purchase_date')} />
        </Field>
        {isEdit ? (
          <Field label="设备状态" hint="报废请通过「报废登记」办理">
            <select value={form.status} onChange={setValue('status')}>
              {(dictionaries?.equipment_status || [])
                .filter((item) => item !== '已报废')
                .map((item) => (
                  <option key={item}>{item}</option>
                ))}
            </select>
          </Field>
        ) : null}
        <Field label="备注" full>
          <textarea rows="2" value={form.remark || ''} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
