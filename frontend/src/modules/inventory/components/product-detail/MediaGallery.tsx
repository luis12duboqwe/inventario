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
      const firstId = data[0]?.id;
      if (firstId) {
        setActive(firstId);
      }
    }
  }, [data, active]);

  const activeUrl = data.find((image) => image.id === active)?.url || data[0]?.url;

  return (
    <div className="grid gap-2">
      <div className="w-full aspect-[4/3] bg-surface rounded-lg grid place-items-center overflow-hidden">
        {activeUrl ? (
          <img src={activeUrl} alt="" className="max-w-full max-h-full object-cover" />
        ) : (
          <span className="text-muted-foreground">Sin imagen</span>
        )}
      </div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(72px,1fr))] gap-2">
        {data.map((image) => (
          <button
            key={image.id}
            onClick={() => setActive(image.id)}
            className={`rounded-lg overflow-hidden border p-0 bg-surface ${
              active === image.id ? "border-primary" : "border-border"
            }`}
          >
            <img src={image.url} alt="" className="w-full h-16 object-cover" />
          </button>
        ))}
      </div>
    </div>
  );
}
