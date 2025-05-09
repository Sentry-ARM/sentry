import {useCallback} from 'react';

import Feature from 'sentry/components/acl/feature';
import {FeatureBadge} from 'sentry/components/core/badge/featureBadge';
import {Button} from 'sentry/components/core/button';
import {ButtonBar} from 'sentry/components/core/button/buttonBar';
import FeedbackWidgetButton from 'sentry/components/feedback/widget/feedbackWidgetButton';
import * as Layout from 'sentry/components/layouts/thirds';
import PageFiltersContainer from 'sentry/components/organizations/pageFilters/container';
import {PageHeadingQuestionTooltip} from 'sentry/components/pageHeadingQuestionTooltip';
import SentryDocumentTitle from 'sentry/components/sentryDocumentTitle';
import {t} from 'sentry/locale';
import {useLocation} from 'sentry/utils/useLocation';
import {useNavigate} from 'sentry/utils/useNavigate';
import useOrganization from 'sentry/utils/useOrganization';
import ExploreBreadcrumb from 'sentry/views/explore/components/breadcrumb';
import {getTitleFromLocation} from 'sentry/views/explore/contexts/pageParamsContext/title';
import {SpansTabContent} from 'sentry/views/explore/spans/spansTab';
import {limitMaxPickableDays} from 'sentry/views/explore/utils';
import {usePrefersStackedNav} from 'sentry/views/nav/prefersStackedNav';

export function ExploreContent() {
  const organization = useOrganization();
  const {defaultPeriod, maxPickableDays, relativeOptions} =
    limitMaxPickableDays(organization);
  const prefersStackedNav = usePrefersStackedNav();

  const location = useLocation();
  const navigate = useNavigate();
  const switchToOldTraceExplorer = useCallback(() => {
    navigate({
      ...location,
      query: {
        ...location.query,
        view: 'trace',
      },
    });
  }, [location, navigate]);

  const hasSavedQueries = organization.features.includes('performance-saved-queries');

  const title = getTitleFromLocation(location);

  return (
    <SentryDocumentTitle title={t('Traces')} orgSlug={organization?.slug}>
      <PageFiltersContainer maxPickableDays={maxPickableDays}>
        <Layout.Page>
          <Layout.Header unified={prefersStackedNav}>
            <Layout.HeaderContent unified={prefersStackedNav}>
              {hasSavedQueries && title ? <ExploreBreadcrumb /> : null}
              <Layout.Title>
                {hasSavedQueries && title ? title : t('Traces')}
                <PageHeadingQuestionTooltip
                  docsUrl="https://github.com/getsentry/sentry/discussions/81239"
                  title={t(
                    'Find problematic spans/traces or compute real-time metrics via aggregation.'
                  )}
                  linkLabel={t('Read the Discussion')}
                />
                <FeatureBadge
                  tooltipProps={{
                    title: t(
                      'This feature is available for early adopters and the UX may change'
                    ),
                  }}
                  type="beta"
                />
              </Layout.Title>
            </Layout.HeaderContent>
            <Layout.HeaderActions>
              <ButtonBar gap={1}>
                <Feature organization={organization} features="visibility-explore-admin">
                  <Button onClick={switchToOldTraceExplorer} size="sm">
                    {t('Switch to Old Trace Explore')}
                  </Button>
                </Feature>
                <FeedbackWidgetButton />
              </ButtonBar>
            </Layout.HeaderActions>
          </Layout.Header>
          <SpansTabContent
            defaultPeriod={defaultPeriod}
            maxPickableDays={maxPickableDays}
            relativeOptions={relativeOptions}
          />
        </Layout.Page>
      </PageFiltersContainer>
    </SentryDocumentTitle>
  );
}
