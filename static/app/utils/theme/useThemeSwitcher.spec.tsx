import {ConfigFixture} from 'sentry-fixture/config';
import {OrganizationFixture} from 'sentry-fixture/organization';

import {act, renderHook, waitFor} from 'sentry-test/reactTestingLibrary';

import ConfigStore from 'sentry/stores/configStore';
import OrganizationStore from 'sentry/stores/organizationStore';
import {removeBodyTheme} from 'sentry/utils/removeBodyTheme';
// eslint-disable-next-line no-restricted-imports -- @TODO(jonasbadalic): Remove theme import
import {darkTheme, lightTheme} from 'sentry/utils/theme/theme';

import {DO_NOT_USE_darkChonkTheme, DO_NOT_USE_lightChonkTheme} from './theme.chonk';
import {useThemeSwitcher} from './useThemeSwitcher';

jest.mock('sentry/utils/removeBodyTheme');

describe('useChonkTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    OrganizationStore.reset();
    ConfigStore.loadInitialData(
      ConfigFixture({
        theme: 'light',
      })
    );
  });

  it('returns null if no organizationis loaded', () => {
    const {result} = renderHook(() => useThemeSwitcher());
    expect(result.current).toBe(lightTheme);
  });

  it('returns old theme if the organization does not have chonk-ui feature', () => {
    OrganizationStore.onUpdate(
      OrganizationFixture({
        features: [],
      })
    );

    const {result} = renderHook(() => useThemeSwitcher());
    expect(result.current).toBe(lightTheme);
  });

  it('returns null if organization has chonk-ui feature and session storage is unset', () => {
    localStorage.clear();
    OrganizationStore.onUpdate(
      OrganizationFixture({
        features: ['chonk-ui'],
      })
    );

    const {result} = renderHook(() => useThemeSwitcher());
    expect(result.current).toBe(lightTheme);
  });

  it('returns light theme if organization has chonk-ui feature and session storage is set to light', () => {
    localStorage.setItem('chonk-theme', JSON.stringify({theme: 'light'}));
    OrganizationStore.onUpdate(
      OrganizationFixture({
        features: ['chonk-ui'],
      })
    );

    const {result} = renderHook(() => useThemeSwitcher());
    expect(result.current).toBe(DO_NOT_USE_lightChonkTheme);
  });

  it('returns dark theme if organization has chonk-ui feature and dark theme is selected', () => {
    localStorage.setItem('chonk-theme', JSON.stringify({theme: 'dark'}));
    OrganizationStore.onUpdate(
      OrganizationFixture({
        features: ['chonk-ui'],
      })
    );

    const {result} = renderHook(() => useThemeSwitcher());
    expect(result.current).toBe(DO_NOT_USE_darkChonkTheme);
  });

  it('unsets chonk theme on config store theme change', async () => {
    localStorage.setItem('chonk-theme', JSON.stringify({theme: 'dark'}));
    OrganizationStore.onUpdate(
      OrganizationFixture({
        features: ['chonk-ui'],
      })
    );

    const {result} = renderHook(() => useThemeSwitcher());

    await waitFor(() => {
      expect(result.current).toBe(DO_NOT_USE_darkChonkTheme);
    });

    act(() => ConfigStore.set('theme', 'dark'));

    expect(result.current).toBe(darkTheme);
    expect(removeBodyTheme).toHaveBeenCalled();
  });

  it('unsets chonk theme if new organization does not have chonk-ui feature', async () => {
    localStorage.setItem('chonk-theme', JSON.stringify({theme: 'dark'}));
    OrganizationStore.onUpdate(
      OrganizationFixture({
        features: ['chonk-ui'],
      })
    );

    const {result} = renderHook(() => useThemeSwitcher());

    await waitFor(() => {
      expect(result.current).toBe(DO_NOT_USE_darkChonkTheme);
    });

    await act(() => {
      OrganizationStore.onUpdate(
        OrganizationFixture({
          features: [],
        })
      );
    });

    await waitFor(() => expect(result.current).toBe(lightTheme));
  });
});
