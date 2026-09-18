import { http } from './client.js';

const RESOURCE = '/equipment';

export const equipmentApi = {
  list: (params) => http.get(RESOURCE, params),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id, params) => http.delete(`${RESOURCE}/${id}`, params),
  reminders: () => http.get(`${RESOURCE}/reminders`),
  addMaintenance: (id, payload) => http.post(`${RESOURCE}/${id}/maintenances`, payload),
  addScrap: (id, payload) => http.post(`${RESOURCE}/${id}/scraps`, payload),
};
