declare module "qrcode" {
  export type QRCodeToDataURLOptions = {
    errorCorrectionLevel?: "L" | "M" | "Q" | "H";
    type?: string;
    margin?: number;
    width?: number;
    scale?: number;
    color?: {
      dark?: string;
      light?: string;
    };
  };

  export function toDataURL(text: string, options?: QRCodeToDataURLOptions): Promise<string>;
}
