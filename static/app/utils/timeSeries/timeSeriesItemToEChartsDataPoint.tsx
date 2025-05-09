import type {TimeSeriesItem} from 'sentry/views/dashboards/widgets/common/types';

export function timeSeriesItemToEChartsDataPoint(
  datum: TimeSeriesItem
): [xAxisValue: number | string, yAxisValue: number | '-'] {
  return [
    datum.timestamp,
    datum.value === null ? ECHARTS_MISSING_DATA_VALUE : datum.value,
  ];
}

// ECharts has a special value to represent missing data, it doesn't nicely
// support `null` or `undefined`
export const ECHARTS_MISSING_DATA_VALUE = `-`;
