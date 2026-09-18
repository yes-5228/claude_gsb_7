export function formatDateTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function formatShortDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

/** 把 Date 或 ISO 字符串转成 datetime-local 输入框需要的值。 */
export function toDateTimeInput(value) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return '';
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export const STATUS_TONES = {
  正常开放: 'tag-success',
  维修中: 'tag-warning',
  暂停使用: 'tag-neutral',
  待整改: 'tag-danger',
  整改中: 'tag-warning',
  待验收: 'tag-info',
  已完成: 'tag-success',
  已关闭: 'tag-neutral',
  正常: 'tag-success',
  发现问题: 'tag-danger',
  在用: 'tag-success',
  已报废: 'tag-neutral',
};

export const MAINTENANCE_DUE_TONES = {
  已逾期: 'tag-danger',
  临近到期: 'tag-warning',
  正常: 'tag-success',
};

export const SEVERITY_TONES = {
  一般: 'tag-neutral',
  严重: 'tag-warning',
  紧急: 'tag-danger',
};

export function statusTone(status) {
  return STATUS_TONES[status] || 'tag-neutral';
}

export function severityTone(severity) {
  return SEVERITY_TONES[severity] || 'tag-neutral';
}

export function maintenanceDueTone(due) {
  return MAINTENANCE_DUE_TONES[due] || 'tag-neutral';
}

/** 距下次保养天数的可读文案，负数表示已逾期天数。 */
export function formatMaintenanceDays(days) {
  if (days === null || days === undefined) return '-';
  if (days < 0) return `已逾期 ${-days} 天`;
  if (days === 0) return '今天到期';
  return `${days} 天后`;
}

export function scoreTone(score) {
  if (score >= 90) return 'score-high';
  if (score >= 70) return 'score-mid';
  return 'score-low';
}

/** 是否超期未整改。 */
export function isOverdue(deadline, status) {
  if (!deadline) return false;
  if (['已完成', '已关闭'].includes(status)) return false;
  return new Date(deadline).getTime() < Date.now();
}
