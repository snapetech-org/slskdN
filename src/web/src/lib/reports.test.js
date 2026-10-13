import api from './api';
import { getTransferSummary } from './reports';

vi.mock('./api', () => ({
  __esModule: true,
  default: { get: vi.fn() },
}));

describe('reports api', () => {
  it('requests the bounded default transfer summary window', async () => {
    const summary = { Download: {}, Upload: {} };
    api.get.mockResolvedValue({ data: summary });

    await expect(getTransferSummary()).resolves.toBe(summary);
    expect(api.get).toHaveBeenCalledWith('/telemetry/reports/transfers/summary');
  });
});
