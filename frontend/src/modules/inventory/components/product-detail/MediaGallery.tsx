import React from "react";

type Image = {
  id: string;
  url: string;
};

type Props = {
  images?: Image[];
};

export default function MediaGallery({ images }: Props) {
  const data = React.useMemo(() => (Array.isArray(images) ? images : []), [images]);
  const [active, setActive] = React.useState<string>(data[0]?.id || "");

  React.useEffect(() => {
    if (!data.length) {
      if (active !== "") {
        setActive("");
      }
      return;
    }

    const hasActiveImage = data.some((image) => image.id === active);
    if (!hasActiveImage) {
      setActive(data[0].id);
    }
  }, [data, active]);

  const activeUrl = data.find((image) => image.id === active)?.url || data[0]?.url;

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div
        style={{
          width: "100%",
          aspectRatio: "4 / 3",
          background: "#0f172a",
          borderRadius: 8,
          display: "grid",
          placeItems: "center",
        }}
      >
        {activeUrl ? (
          <img src={activeUrl} alt="" style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "cover" }} />
        ) : (
          <span style={{ color: "#64748b" }}>Sin imagen</span>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(72px,1fr))", gap: 6 }}>
        {data.map((image) => (
          <button
            key={image.id}
            onClick={() => setActive(image.id)}
            style={{
              borderRadius: 8,
              overflow: "hidden",
              border: active === image.id ? "2px solid #2563eb" : "1px solid rgba(255,255,255,0.08)",
              padding: 0,
              background: "#0f172a",
            }}
          >
            <img src={image.url} alt="" style={{ width: "100%", height: 64, objectFit: "cover" }} />
          </button>
        ))}
      </div>
    </div>
  );
}
