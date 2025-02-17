import {normalizeDateTimeParams} from 'sentry/components/organizations/pageFilters/parse';
import type {DateString, PageFilters} from 'sentry/types/core';
import type {MetricAggregation, MRI} from 'sentry/types/metrics';
import {useApiQuery} from 'sentry/utils/queryClient';
import useOrganization from 'sentry/utils/useOrganization';
import usePageFilters from 'sentry/utils/usePageFilters';

/**
 * This type is incomplete as there are other fields available.
 */
type FieldTypes = {
  id: string;
  'profile.id': string | null;
  project: string;
  'project.id': number;
  'span.description': string;
  'span.duration': number;
  'span.op': string;
  'span.self_time': number;
  timestamp: DateString;
  trace: string;
  transaction: string;
  // There are some spans where the transaction id can be null
  // because they're not associated to any transactions such
  // as the INP spans.
  'transaction.id': string | null;
};

export type Summary = {
  count: number;
  max: number;
  min: number;
  sum: number;
};

type ResultFieldTypes = FieldTypes & {
  summary: Summary;
};

export type Field = keyof FieldTypes;
export type ResultField = keyof ResultFieldTypes;

interface UseMetricSamplesOptions<F extends Field> {
  fields: F[];
  referrer: string;
  aggregation?: MetricAggregation;
  datetime?: PageFilters['datetime'];
  enabled?: boolean;
  limit?: number;
  max?: number;
  min?: number;
  mri?: MRI;
  query?: string;
  sort?: string;
}

export interface MetricsSamplesResults<F extends Field> {
  data: Array<Pick<ResultFieldTypes, F | 'summary'>>;
  meta: any; // not going to type this yet
}

export function useMetricsSamples<F extends Field>({
  datetime,
  enabled,
  fields,
  limit,
  max,
  min,
  mri,
  aggregation,
  referrer,
  query,
  sort,
}: UseMetricSamplesOptions<F>) {
  const organization = useOrganization();
  const {selection} = usePageFilters();

  const path = `/organizations/${organization.slug}/metrics/samples/`;

  const endpointOptions = {
    query: {
      project: selection.projects,
      environment: selection.environments,
      ...normalizeDateTimeParams(datetime ?? selection.datetime),
      field: fields,
      max,
      min,
      mri,
      operation: aggregation,
      query,
      referrer,
      per_page: limit,
      sort,
    },
  };

  return useApiQuery<MetricsSamplesResults<F>>([path, endpointOptions], {
    staleTime: 0,
    refetchOnWindowFocus: false,
    retry: false,
    enabled,
  });
}

export function getSummaryValueForAggregation(
  summary: Summary,
  aggregation?: MetricAggregation
) {
  switch (aggregation) {
    case 'count':
      return summary.count;
    case 'min':
      return summary.min;
    case 'max':
      return summary.max;
    case 'sum':
      return summary.sum;
    case 'avg':
    default:
      return summary.sum / summary.count;
  }
}
