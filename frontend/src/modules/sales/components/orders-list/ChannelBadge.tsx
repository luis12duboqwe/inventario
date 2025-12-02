import React from "react";

export type ChannelBadgeProps = {
  value: "POS" | "WEB" | "MANUAL" | string;
};

function ChannelBadge({ value }: ChannelBadgeProps) {
  const getBadgeClass = (channel: string) => {
    switch (channel) {
      case "POS":
        return "orders-channel-badge--pos";
      case "WEB":
        return "orders-channel-badge--web";
      case "MANUAL":
        return "orders-channel-badge--manual";
      default:
        return "orders-channel-badge--default";
    }
  };

  return <span className={`orders-channel-badge ${getBadgeClass(value)}`}>{value}</span>;
}

export default ChannelBadge;
