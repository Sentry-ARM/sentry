import {Fragment, useRef} from 'react';
import {css} from '@emotion/react';
import styled from '@emotion/styled';
import {useHover} from '@react-aria/interactions';

import ErrorBoundary from 'sentry/components/errorBoundary';
import EventOrGroupTitle from 'sentry/components/eventOrGroupTitle';
import EventMessage from 'sentry/components/events/eventMessage';
import Link from 'sentry/components/links/link';
import {IconStar} from 'sentry/icons';
import {tct} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import type {Event} from 'sentry/types/event';
import type {Group, GroupTombstoneHelper} from 'sentry/types/group';
import type {Organization} from 'sentry/types/organization';
import {getLocation, getMessage, isGroup, isTombstone} from 'sentry/utils/events';
import {fetchDataQuery, useQueryClient} from 'sentry/utils/queryClient';
import {useLocation} from 'sentry/utils/useLocation';
import useOrganization from 'sentry/utils/useOrganization';
import usePageFilters from 'sentry/utils/usePageFilters';
import {makeFetchGroupQueryKey} from 'sentry/views/issueDetails/useGroup';
import {createIssueLink} from 'sentry/views/issueList/utils';

import EventTitleError from './eventTitleError';

interface EventOrGroupHeaderProps {
  data: Event | Group | GroupTombstoneHelper;
  eventId?: string;
  hideIcons?: boolean;
  hideLevel?: boolean;
  index?: number;
  /** Group link clicked */
  onClick?: () => void;
  query?: string;
  source?: string;
}

function usePreloadGroupOnHover({
  groupId,
  disabled,
  organization,
}: {
  disabled: boolean;
  groupId: string;
  organization: Organization;
}) {
  const queryClient = useQueryClient();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const {selection} = usePageFilters();

  const {hoverProps} = useHover({
    onHoverStart: () => {
      timeoutRef.current = setTimeout(() => {
        queryClient.prefetchQuery({
          queryKey: makeFetchGroupQueryKey({
            groupId,
            organizationSlug: organization.slug,
            environments: selection.environments,
          }),
          queryFn: fetchDataQuery,
          staleTime: 30_000,
        });
      }, 300);
    },
    onHoverEnd: () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    },
    isDisabled: disabled,
  });

  return hoverProps;
}

/**
 * Displays an event or group/issue title (i.e. in Stream)
 */
function EventOrGroupHeader({
  data,
  index,
  query,
  onClick,
  hideIcons,
  eventId,
  source,
}: EventOrGroupHeaderProps) {
  const location = useLocation();
  const organization = useOrganization();

  const hasNewLayout = organization.features.includes('issue-stream-table-layout');
  const preloadHoverProps = usePreloadGroupOnHover({
    groupId: data.id,
    disabled: !hasNewLayout || isTombstone(data) || !isGroup(data),
    organization,
  });

  function getTitleChildren() {
    const {isBookmarked, hasSeen} = data as Group;
    return (
      <Fragment>
        {!hideIcons && isBookmarked && (
          <IconWrapper>
            <IconStar isSolid color="yellow300" />
          </IconWrapper>
        )}
        <ErrorBoundary customComponent={() => <EventTitleError />} mini>
          <StyledEventOrGroupTitle
            data={data}
            // hasSeen is undefined for GroupTombstone
            hasSeen={hasSeen === undefined ? true : hasSeen}
            withStackTracePreview
            query={query}
            hasNewLayout={hasNewLayout}
          />
        </ErrorBoundary>
      </Fragment>
    );
  }

  function getTitle() {
    const {status} = data as Group;

    const commonEleProps = {
      'data-test-id': status === 'resolved' ? 'resolved-issue' : null,
    };

    if (isTombstone(data)) {
      return (
        <TitleWithoutLink {...commonEleProps}>{getTitleChildren()}</TitleWithoutLink>
      );
    }

    const to = createIssueLink({
      organization,
      data,
      eventId,
      referrer: source,
      streamIndex: index,
      location,
      query,
    });

    if (hasNewLayout) {
      return (
        <NewTitleWithLink
          {...commonEleProps}
          {...preloadHoverProps}
          to={to}
          onClick={onClick}
          data-issue-title-link
        >
          {getTitleChildren()}
        </NewTitleWithLink>
      );
    }

    return (
      <TitleWithLink {...commonEleProps} to={to} onClick={onClick}>
        {getTitleChildren()}
      </TitleWithLink>
    );
  }

  const eventLocation = getLocation(data);

  return (
    <div data-test-id="event-issue-header">
      <Title>{getTitle()}</Title>
      {eventLocation && !hasNewLayout ? <Location>{eventLocation}</Location> : null}
      <StyledEventMessage
        data={data}
        level={'level' in data ? data.level : undefined}
        message={getMessage(data)}
        type={data.type}
        levelIndicatorSize={9}
      />
    </div>
  );
}

const truncateStyles = css`
  overflow: hidden;
  max-width: 100%;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const Title = styled('div')`
  margin-bottom: ${space(0.25)};
  font-size: ${p => p.theme.fontSizeLarge};
  & em {
    font-size: ${p => p.theme.fontSizeMedium};
    font-style: normal;
    font-weight: ${p => p.theme.fontWeightNormal};
    color: ${p => p.theme.subText};
  }
`;

const LocationWrapper = styled('div')`
  ${truncateStyles};
  margin: 0 0 5px;
  direction: rtl;
  text-align: left;
  font-size: ${p => p.theme.fontSizeMedium};
  color: ${p => p.theme.subText};
  span {
    direction: ltr;
  }
`;

function Location(props: any) {
  const {children, ...rest} = props;
  return (
    <LocationWrapper {...rest}>
      {tct('in [location]', {
        location: <span>{children}</span>,
      })}
    </LocationWrapper>
  );
}

const StyledEventMessage = styled(EventMessage)`
  margin: 0 0 5px;
  font-size: inherit;
`;

const IconWrapper = styled('span')`
  position: relative;
  margin-right: 5px;
`;

const TitleWithLink = styled(Link)`
  display: inline-flex;
  align-items: center;
`;

const NewTitleWithLink = styled(Link)`
  ${p => p.theme.overflowEllipsis};
  color: ${p => p.theme.textColor};

  &:hover {
    color: ${p => p.theme.textColor};
  }
`;

const TitleWithoutLink = styled('span')`
  ${p => p.theme.overflowEllipsis};
`;

export default EventOrGroupHeader;

const StyledEventOrGroupTitle = styled(EventOrGroupTitle)<{
  hasNewLayout: boolean;
  hasSeen: boolean;
}>`
  font-weight: ${p =>
    p.hasSeen && !p.hasNewLayout ? p.theme.fontWeightNormal : p.theme.fontWeightBold};
`;
