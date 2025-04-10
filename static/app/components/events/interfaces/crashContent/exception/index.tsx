import ErrorBoundary from 'sentry/components/errorBoundary';
import type {Event, ExceptionType} from 'sentry/types/event';
import type {Group} from 'sentry/types/group';
import type {Project} from 'sentry/types/project';
import type {StackType} from 'sentry/types/stacktrace';
import {StackView} from 'sentry/types/stacktrace';

import {Content} from './content';
import RawContent from './rawContent';

type Props = {
  event: Event;
  newestFirst: boolean;
  projectSlug: Project['slug'];
  stackType: StackType;
  values: ExceptionType['values'];
  groupingCurrentLevel?: Group['metadata']['current_level'];
  meta?: Record<any, any>;
  stackView?: StackView;
  threadId?: number;
};

export function ExceptionContent({
  stackView,
  stackType,
  projectSlug,
  values,
  event,
  newestFirst,
  groupingCurrentLevel,
  meta,
  threadId,
}: Props) {
  return (
    <ErrorBoundary mini>
      {stackView === StackView.RAW ? (
        <RawContent
          eventId={event.id}
          projectSlug={projectSlug}
          type={stackType}
          values={values}
          platform={event.platform}
        />
      ) : (
        <Content
          type={stackType}
          stackView={stackView}
          values={values}
          projectSlug={projectSlug}
          newestFirst={newestFirst}
          event={event}
          groupingCurrentLevel={groupingCurrentLevel}
          meta={meta}
          threadId={threadId}
        />
      )}
    </ErrorBoundary>
  );
}
