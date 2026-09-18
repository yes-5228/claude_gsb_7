import { useState } from 'react';

import { equipmentApi } from '../../api/equipment.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { toDateTimeInput } from '../../utils/format.js';

export default function ScrapFormModal({ equipment, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const available = equipment?.available_quantity ?? 0;
  const [form, setForm] = useState(() => ({
    scrapped_at: toDateTimeInput(new Date()),
    quantity: 1,
    reason: '',
    disposal_method: '回收处理',
    operator: '',
    remark: '',
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
    if (!form.reason.trim() || !form.operator.trim()) {
      setError('报废原因与经办人为必填项');
      return;
    }
    if (!form.quantity || form.quantity < 1 || form.quantity > available) {
      setError(`报废数量需在 1 ~ ${available} 之间`);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await equipmentApi.addScrap(equipment.id, {
        scrapped_at: form.scrapped_at ? new Date(form.scrapped_at).toISOString() : null,
        quantity: form.quantity,
        reason: form.reason.trim(),
        disposal_method: form.disposal_method,
        operator: form.operator.trim(),
        remark: form.remark.trim() || null,
      });
      toast.success(form.quantity >= available ? '已全部报废，设备状态转为「已报废」' : '报废记录已登记');
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
      title={`报废登记 - ${equipment.name}（${equipment.code}）`}
      onClose={onClose}
      width={720}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="scrap-form" className="btn btn-primary" disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      {form.quantity >= available ? (
        <div className="alert alert-info">本次报废数量为全部可用数量，保存后设备将转为「已报废」。</div>
      ) : null}
      <form id="scrap-form" className="form-grid" onSubmit={submit}>
        <Field label="报废时间">
          <input
            type="datetime-local"
            value={form.scrapped_at}
            onChange={setValue('scrapped_at')}
          />
        </Field>
        <Field label={`报废数量 *（可用 ${available} ${equipment.unit}）`}>
          <input
            type="number"
            min="1"
            max={available}
            value={form.quantity}
            onChange={setValue('quantity')}
          />
        </Field>
        <Field label="报废原因 *" full>
          <textarea
            rows="2"
            value={form.reason}
            onChange={setValue('reason')}
            placeholder="如：拖杆断裂无法修复、电机烧毁"
          />
        </Field>
        <Field label="处置方式">
          <select value={form.disposal_method} onChange={setValue('disposal_method')}>
            {(dictionaries?.disposal_method || ['回收处理']).map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="经办人 *">
          <input value={form.operator} onChange={setValue('operator')} placeholder="登记报废的人员" />
        </Field>
        <Field label="备注" full>
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
