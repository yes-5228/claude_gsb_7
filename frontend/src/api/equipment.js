import { http } from './client.js';

const RESOURCE = '/equipment';

export const equipmentApi = {
  list: (params) => http.get(RESOURCE, params),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id, params) => http.delete(`${RESOURCE}/${id}`, params),
  reminders: (days) => http.get(`${RESOURCE}/reminders`, days ? { days } : undefined),
  addMaintenance: (id, payload) => http.post(`${RESOURCE}/${id}/maintenance`, payload),
  scrap: (id, payload) => http.post(`${RESOURCE}/${id}/scrap`, payload),
};
