import type {SVGIconProps} from './svgIcon';
import {SvgIcon} from './svgIcon';

function IconVsts(props: SVGIconProps) {
  return (
    <SvgIcon {...props} kind="path">
      <polygon points="0 5.85 1.54 3.81 6.84 2.3 6.84 0 12.57 3.43 2.27 5.54 2.27 11.42 0 10.43 0 5.85" />
      <polygon points="12.57 3.43 12.57 12.23 2.27 11.42 5.7 16 5.7 13.7 11.91 16 16 12.69 16 2.9 12.57 3.43" />
    </SvgIcon>
  );
}

IconVsts.displayName = 'IconVsts';

export {IconVsts};
