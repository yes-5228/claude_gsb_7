import { useState } from 'react';

import { equipmentApi } from '../../api/equipment.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { toDateTimeInput } from '../../utils/format.js';

const EMPTY = {
  name: '',
  category: '保洁工具',
  quantity: 1,
  unit: '台',
  assignee: '',
  location: '',
  maintenance_cycle: '每月',
  last_maintained_at: '',
  remark: '',
};

export default function EquipmentFormModal({ equipment, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [form, setForm] = useState(() => ({
    ...EMPTY,
    ...(equipment ?? {}),
    last_maintained_at: equipment?.last_maintained_at
      ? toDateTimeInput(equipment.last_maintained_at)
      : '',
    remark: equipment?.remark ?? '',
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (event) => {
    const target = event.target;
    const value = target.type === 'number' ? Number(target.value) : target.value;
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) {
      setError('工具/设备名称为必填项');
      return;
    }
    if (!form.quantity || form.quantity < 1) {
      setError('配置数量至少为 1');
      return;
    }
    setSaving(true);
    setError(null);
    const payload = {
      name: form.name.trim(),
      category: form.category,
      quantity: form.quantity,
      unit: form.unit.trim() || '台',
      assignee: form.assignee.trim(),
      location: form.location.trim(),
      maintenance_cycle: form.maintenance_cycle,
      remark: form.remark?.trim() || null,
    };
    try {
      if (equipment?.id) {
        await equipmentApi.update(equipment.id, payload);
        toast.success('设备信息已更新');
      } else {
        await equipmentApi.create({
          ...payload,
          last_maintained_at: form.last_maintained_at
            ? new Date(form.last_maintained_at).toISOString()
            : null,
        });
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
      title={equipment?.id ? `编辑设备 - ${equipment.code}` : '登记工具设备'}
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
        <Field label="名称 *">
          <input value={form.name} onChange={setValue('name')} placeholder="如：高压冲洗机" />
        </Field>
        <Field label="分类">
          <select value={form.category} onChange={setValue('category')}>
            {(dictionaries?.equipment_category || ['保洁工具']).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="配置数量 *">
          <input type="number" min="1" value={form.quantity} onChange={setValue('quantity')} />
        </Field>
        <Field label="计量单位">
          <input value={form.unit} onChange={setValue('unit')} placeholder="台 / 把 / 辆" />
        </Field>
        <Field label="使用人">
          <input value={form.assignee} onChange={setValue('assignee')} placeholder="责任保洁员" />
        </Field>
        <Field label="存放地点">
          <input value={form.location} onChange={setValue('location')} placeholder="如：城东设备间" />
        </Field>
        <Field label="保养周期" hint={equipment?.id ? '调整周期后将重新推算下次保养日期' : undefined}>
          <select value={form.maintenance_cycle} onChange={setValue('maintenance_cycle')}>
            {(dictionaries?.maintenance_cycle || ['每月']).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        {equipment?.id ? null : (
          <Field label="最近保养时间" hint="留空按建档时间起算下次保养日期">
            <input
              type="datetime-local"
              value={form.last_maintained_at}
              onChange={setValue('last_maintained_at')}
            />
          </Field>
        )}
        <Field label="备注" full>
          <textarea rows="2" value={form.remark || ''} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
