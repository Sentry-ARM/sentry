import {OrganizationFixture} from 'sentry-fixture/organization';

import {render, screen} from 'sentry-test/reactTestingLibrary';

import Nav from 'sentry/views/nav';
import {NavContextProvider} from 'sentry/views/nav/context';

jest.mock('sentry/utils/analytics', () => ({
  trackAnalytics: jest.fn(),
}));

const ALL_AVAILABLE_FEATURES = ['codecov-ui'];

describe('PipelineSecondaryNav', () => {
  beforeEach(() => {
    localStorage.clear();
    MockApiClient.clearMockResponses();

    MockApiClient.addMockResponse({
      url: `/organizations/org-slug/broadcasts/`,
      body: [],
    });

    MockApiClient.addMockResponse({
      url: `/assistant/`,
      body: [],
    });
  });

  it('renders the passed children', () => {
    render(
      <NavContextProvider>
        <Nav />
        <div id="main" />
      </NavContextProvider>,
      {
        enableRouterMocks: false,
        initialRouterConfig: {
          location: {
            pathname: '/organizations/test-org-slug/pipeline/',
          },
        },
      }
    );

    expect(screen.getByText('Pipeline')).toBeInTheDocument();
  });

  it('renders the correct coverage link', () => {
    render(
      <NavContextProvider>
        <Nav />
        <div id="main" />
      </NavContextProvider>,
      {
        organization: OrganizationFixture({features: ALL_AVAILABLE_FEATURES}),
        enableRouterMocks: false,
        initialRouterConfig: {
          location: {
            pathname: '/organizations/test-org-slug/pipeline/coverage/',
          },
        },
      }
    );

    const coverageLink = screen.getByText('Coverage');
    expect(coverageLink).toBeInTheDocument();
    // TODO: @nicholas-codecov this link should appear once routes have been added
    expect(coverageLink).not.toHaveAttribute('href');
  });

  it('renders the correct tests link', () => {
    render(
      <NavContextProvider>
        <Nav />
        <div id="main" />
      </NavContextProvider>,
      {
        organization: OrganizationFixture({features: ALL_AVAILABLE_FEATURES}),
        enableRouterMocks: false,
        initialRouterConfig: {
          location: {
            pathname: '/organizations/test-org-slug/pipeline/tests/',
          },
        },
      }
    );

    const testsLink = screen.getByText('Tests');
    expect(testsLink).toBeInTheDocument();
    // TODO: @nicholas-codecov this link should appear once routes have been added
    expect(testsLink).not.toHaveAttribute('href');
  });
});
