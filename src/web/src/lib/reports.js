import api from './api';

export const getTransferSummary = async () => {
  const response = await api.get('/telemetry/reports/transfers/summary');
  return response.data;
};
