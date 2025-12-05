import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { inventoryService } from "../../services/inventoryService";
import { InventoryReservationInput, InventoryReservationRenewInput } from "@api/inventory";

export function useInventoryReservations(
  token: string,
  storeId: number | null,
  page: number,
  pageSize: number,
  includeExpired: boolean
) {
  const queryClient = useQueryClient();
  const queryKey = ["inventoryReservations", storeId, page, pageSize, includeExpired];

const query = useQuery({
    queryKey,
    queryFn: async () => {
      if (!storeId) {
        return {
          items: [],
          page: 1,
          size: pageSize,
          total: 0,
          pages: 0,
          has_next: false,
        };
      }
      return inventoryService.fetchReservations(token, {
        storeId,
        page,
        size: pageSize,
        includeExpired,
      });
    },
    enabled: !!storeId && !!token,
});

  const createMutation = useMutation({
    mutationFn: ({ input, reason }: { input: Omit<InventoryReservationInput, "store_id">; reason: string }) => {
      if (!storeId) throw new Error("Selecciona una sucursal antes de reservar inventario");
      return inventoryService.createReservation(token, { ...input, store_id: storeId }, reason);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventoryReservations"] });
    },
  });

  const renewMutation = useMutation({
    mutationFn: ({ reservationId, input, reason }: { reservationId: number; input: InventoryReservationRenewInput; reason: string }) => {
      return inventoryService.renewReservation(token, reservationId, input, reason);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventoryReservations"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: ({ reservationId, reason }: { reservationId: number; reason: string }) => {
      return inventoryService.cancelReservation(token, reservationId, reason);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventoryReservations"] });
    },
  });

  return {
    ...query,
    createReservation: createMutation.mutateAsync,
    renewReservation: renewMutation.mutateAsync,
    cancelReservation: cancelMutation.mutateAsync,
  };
}
