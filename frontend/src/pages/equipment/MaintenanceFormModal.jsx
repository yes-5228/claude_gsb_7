import { useState } from 'react';

import { equipmentApi } from '../../api/equipment.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { toDateTimeInput } from '../../utils/format.js';

export default function MaintenanceFormModal({ equipment, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState(() => ({
    maintained_at: toDateTimeInput(new Date()),
    operator: equipment?.assignee || '',
    content: '',
    replaced_parts: '',
    cost: '',
    remark: '',
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.operator.trim() || !form.content.trim()) {
      setError('保养人与保养内容为必填项');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await equipmentApi.addMaintenance(equipment.id, {
        maintained_at: form.maintained_at ? new Date(form.maintained_at).toISOString() : null,
        operator: form.operator.trim(),
        content: form.content.trim(),
        replaced_parts: form.replaced_parts.trim(),
        cost: form.cost === '' ? null : Number(form.cost),
        remark: form.remark.trim() || null,
      });
      toast.success('保养记录已登记，下次保养日期已顺延');
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
      title={`登记保养 - ${equipment.name}（${equipment.code}）`}
      onClose={onClose}
      width={720}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="maintenance-form"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <div className="alert alert-info">
        保养周期「{equipment.maintenance_cycle}」，保存后下次保养日期将自保养时间起顺延一个周期。
      </div>
      <form id="maintenance-form" className="form-grid" onSubmit={submit}>
        <Field label="保养时间">
          <input
            type="datetime-local"
            value={form.maintained_at}
            onChange={setValue('maintained_at')}
          />
        </Field>
        <Field label="保养人 *">
          <input value={form.operator} onChange={setValue('operator')} placeholder="执行保养的人员" />
        </Field>
        <Field label="保养内容 *" full>
          <textarea
            rows="3"
            value={form.content}
            onChange={setValue('content')}
            placeholder="如：清洗泵头与滤网、链条上油、整机消毒"
          />
        </Field>
        <Field label="更换部件">
          <input
            value={form.replaced_parts}
            onChange={setValue('replaced_parts')}
            placeholder="如：密封圈、刷盘，无则留空"
          />
        </Field>
        <Field label="保养费用（元）">
          <input
            type="number"
            min="0"
            step="0.01"
            value={form.cost}
            onChange={setValue('cost')}
            placeholder="0"
          />
        </Field>
        <Field label="备注" full>
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
