import {vec2} from 'gl-matrix';
import {ThemeFixture} from 'sentry-fixture/theme';

import {makeLightFlamegraphTheme} from 'sentry/utils/profiling/flamegraph/flamegraphTheme';
import {transformMatrixBetweenRect} from 'sentry/utils/profiling/gl/utils';
import {CursorRenderer} from 'sentry/utils/profiling/renderers/cursorRenderer';
import {Rect} from 'sentry/utils/profiling/speedscope';

const theme = makeLightFlamegraphTheme(ThemeFixture());

describe('CursorRenderer', () => {
  it('renders cursor in center screen', () => {
    const context = {
      beginPath: jest.fn(),
      moveTo: jest.fn(),
      lineTo: jest.fn(),
      strokeStyle: undefined,
      stroke: jest.fn(),
    };
    const canvasMock = {
      getContext: jest.fn().mockReturnValue(context),
    } as unknown as HTMLCanvasElement;

    const renderer = new CursorRenderer(canvasMock, theme);

    const cursor = vec2.fromValues(0.5, 0.5);
    const physicalSpace = new Rect(0, 0, 1000, 1000);

    const configViewToPhysicalSpace = transformMatrixBetweenRect(
      new Rect(0, 0, 1, 1),
      physicalSpace
    );

    renderer.draw(cursor, physicalSpace, configViewToPhysicalSpace);

    expect(context.beginPath).toHaveBeenCalled();

    // Draws vertical line
    expect(context.moveTo.mock.calls[0]).toEqual([500, 0]);
    expect(context.lineTo.mock.calls[0]).toEqual([500, 1000]);

    // Draws horizontal line
    expect(context.moveTo.mock.calls[1]).toEqual([0, 500]);
    expect(context.lineTo.mock.calls[1]).toEqual([1000, 500]);

    expect(context.strokeStyle).toBe(theme.COLORS.CURSOR_CROSSHAIR);
    expect(context.stroke).toHaveBeenCalledTimes(1);
  });
});
