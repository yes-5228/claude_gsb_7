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
    content: '',
    replaced_parts: '',
    operator: equipment?.custodian || '',
    remark: '',
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.content.trim()) {
      setError('保养内容为必填项');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await equipmentApi.addMaintenance(equipment.id, {
        maintained_at: form.maintained_at ? new Date(form.maintained_at).toISOString() : null,
        content: form.content.trim(),
        replaced_parts: form.replaced_parts.trim() || null,
        operator: form.operator.trim(),
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
      width={640}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="maintenance-form" className="btn btn-primary" disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="maintenance-form" className="form-grid" onSubmit={submit}>
        <Field label="保养时间">
          <input
            type="datetime-local"
            value={form.maintained_at}
            onChange={setValue('maintained_at')}
          />
        </Field>
        <Field label="保养人">
          <input value={form.operator} onChange={setValue('operator')} placeholder="执行保养的人员" />
        </Field>
        <Field label="保养内容 *" full>
          <textarea
            rows="3"
            value={form.content}
            onChange={setValue('content')}
            placeholder="如：更换刷盘、清洗滤网、检查电瓶与线路"
          />
        </Field>
        <Field label="更换部件" full hint="无更换部件可留空">
          <input
            value={form.replaced_parts}
            onChange={setValue('replaced_parts')}
            placeholder="如：刷盘×2、密封圈"
          />
        </Field>
        <Field label="备注" full>
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
