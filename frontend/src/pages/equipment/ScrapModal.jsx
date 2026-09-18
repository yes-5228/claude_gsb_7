import { useState } from 'react';

import { equipmentApi } from '../../api/equipment.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';

export default function ScrapModal({ equipment, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [form, setForm] = useState(() => ({
    reason: '',
    disposal_method: dictionaries?.disposal_method?.[0] || '回收处理',
    remark: '',
  }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const setValue = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!form.reason.trim()) {
      setError('报废原因为必填项');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await equipmentApi.scrap(equipment.id, {
        reason: form.reason.trim(),
        disposal_method: form.disposal_method,
        remark: form.remark.trim() || null,
      });
      toast.success('报废登记完成');
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
      width={560}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button type="submit" form="scrap-form" className="btn btn-danger" disabled={saving}>
            {saving ? '提交中…' : '确认报废'}
          </button>
        </>
      }
    >
      <div className="alert alert-info">
        报废后设备状态将置为「已报废」，不再参与保养提醒，且不可再编辑或登记保养。
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="scrap-form" className="form-grid" onSubmit={submit}>
        <Field label="报废原因 *" full>
          <textarea
            rows="3"
            value={form.reason}
            onChange={setValue('reason')}
            placeholder="如：电机烧毁无法修复 / 老化损坏维修成本过高"
          />
        </Field>
        <Field label="处置方式 *">
          <select value={form.disposal_method} onChange={setValue('disposal_method')}>
            {(dictionaries?.disposal_method || ['回收处理', '变卖处理', '废弃处理', '其他']).map(
              (item) => (
                <option key={item}>{item}</option>
              ),
            )}
          </select>
        </Field>
        <Field label="处置说明" full hint="可填写回收单号、经办人等信息">
          <textarea rows="2" value={form.remark} onChange={setValue('remark')} />
        </Field>
      </form>
    </Modal>
  );
}
