import {EventFixture} from 'sentry-fixture/event';
import {GroupFixture} from 'sentry-fixture/group';
import {ProjectFixture} from 'sentry-fixture/project';

import {EntryType} from 'sentry/types';
import {BreadcrumbLevelType, BreadcrumbType} from 'sentry/types/breadcrumbs';

const oneMinuteBeforeEventFixture = '2019-05-21T18:00:48.76Z';
export const MOCK_BREADCRUMBS = [
  {
    message: 'warning',
    category: 'Warning Category',
    level: BreadcrumbLevelType.WARNING,
    type: BreadcrumbType.INFO,
    timestamp: oneMinuteBeforeEventFixture,
  },
  {
    message: 'log',
    category: 'Log Category',
    level: BreadcrumbLevelType.LOG,
    type: BreadcrumbType.INFO,
    timestamp: oneMinuteBeforeEventFixture,
  },
  {
    message: 'request',
    category: 'Request Category',
    level: BreadcrumbLevelType.INFO,
    type: BreadcrumbType.NAVIGATION,
    timestamp: oneMinuteBeforeEventFixture,
  },
  {
    message: 'query',
    category: 'Query Category',
    level: BreadcrumbLevelType.INFO,
    type: BreadcrumbType.QUERY,
    timestamp: oneMinuteBeforeEventFixture,
  },
];
const MOCK_BREADCRUMB_ENTRY = {
  type: EntryType.BREADCRUMBS,
  data: {
    values: MOCK_BREADCRUMBS,
  },
};
export const MOCK_EXCEPTION_ENTRY = {
  type: EntryType.EXCEPTION,
  data: {
    values: [
      {
        value: 'Error',
      },
    ],
  },
};
export const MOCK_DATA_SECTION_PROPS = {
  event: EventFixture({
    id: 'abc123def456ghi789jkl',
    entries: [MOCK_BREADCRUMB_ENTRY, MOCK_EXCEPTION_ENTRY],
  }),
  project: ProjectFixture(),
  group: GroupFixture(),
};