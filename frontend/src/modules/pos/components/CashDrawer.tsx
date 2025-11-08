import CashPanel from "../../operations/components/pos/CashPanel";
import type { PosSessionSummary } from "../../../services/api/pos";

export type StoreOption = {
  id: number;
  name: string;
};

export type CashDrawerProps = {
  stores: StoreOption[];
  selectedStoreId: number | null;
  onStoreChange: (storeId: number) => void;
  session: PosSessionSummary | null;
  onOpenSession: (payload: { amount: number; notes: string; reason: string }) => Promise<void>;
  onCloseSession: (payload: { amount: number; notes: string; reason: string }) => Promise<void>;
  refreshing: boolean;
  onRefresh: () => void;
  error?: string | null;
};

export default function CashDrawer(props: CashDrawerProps) {
  return <CashPanel {...props} />;
}
