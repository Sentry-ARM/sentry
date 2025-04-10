import type {SVGIconProps} from './svgIcon';
import {SvgIcon} from './svgIcon';

/**
 * @deprecated This icon will be removed in new UI.
 */
function IconDiamond(props: SVGIconProps) {
  return (
    <SvgIcon {...props} kind={'path'}>
      <path d="M8,16a.74.74,0,0,1-.53-.22L.21,8.53a.75.75,0,0,1,0-1.06L7.47.21a.75.75,0,0,1,1.06,0l7.26,7.26a.75.75,0,0,1,0,1.06L8.53,15.79A.74.74,0,0,1,8,16Z" />
    </SvgIcon>
  );
}

IconDiamond.displayName = 'IconDiamond';

export {IconDiamond};
