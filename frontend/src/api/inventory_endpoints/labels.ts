import { request, API_URL, parseFilenameFromDisposition } from "../client";
import {
    DeviceLabelFormat,
    DeviceLabelTemplate,
    LabelConnectorInput,
    DeviceLabelDownload,
    DeviceLabelCommands,
} from "../inventoryTypes";
import { PosHardwareActionResponse } from "../pos";

export async function requestDeviceLabel(
  token: string,
  storeId: number,
  deviceId: number,
  reason: string,
  options: {
    format?: DeviceLabelFormat;
    template?: DeviceLabelTemplate;
    printerName?: string | null;
  } = {},
): Promise<DeviceLabelDownload | DeviceLabelCommands> {
  const format = options.format ?? "pdf";
  const template = options.template ?? "38x25";
  const url = new URL(
    `${API_URL}/inventory/stores/${storeId}/devices/${deviceId}/label/${format}`,
  );
  url.searchParams.set("template", template);
  if (options.printerName) {
    url.searchParams.set("printer_name", options.printerName);
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Reason": reason,
  };
  headers.Accept = format === "pdf" ? "application/pdf" : "application/json";

  const response = await fetch(url.toString(), {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    throw new Error("No fue posible generar la etiqueta del dispositivo.");
  }

  if (format === "pdf") {
    const blob = await response.blob();
    const disposition = response.headers.get("content-disposition");
    const fallback = `etiqueta_${storeId}_${deviceId}.pdf`;
    const filename = parseFilenameFromDisposition(disposition, fallback);
    return { blob, filename };
  }

  const payload = (await response.json()) as DeviceLabelCommands;
  return payload;
}

export async function triggerDeviceLabelPrint(
  token: string,
  storeId: number,
  deviceId: number,
  reason: string,
  payload: { format: DeviceLabelFormat; template: DeviceLabelTemplate; connector?: LabelConnectorInput | null },
): Promise<PosHardwareActionResponse> {
  return request<PosHardwareActionResponse>(
    `/inventory/stores/${storeId}/devices/${deviceId}/label/print`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        "X-Reason": reason,
      },
    },
    token,
  );
}
