import React from "react";

import POSAmountPad, { type POSAmountPadProps } from "../pos-drawer/AmountPad";

type AmountPadProps = POSAmountPadProps;

function AmountPad(props: AmountPadProps) {
  return <POSAmountPad {...props} />;
}

export type { AmountPadProps };
export default AmountPad;
