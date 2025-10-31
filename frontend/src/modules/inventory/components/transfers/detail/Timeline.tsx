export type TimelineStep = {
  id: string;
  label: string;
  description?: string;
  completed?: boolean;
  active?: boolean;
  date?: string;
};

type Props = {
  steps?: TimelineStep[];
};

function Timeline({ steps }: Props) {
  const list = Array.isArray(steps) ? steps : [];

  return (
    <ol className="transfer-timeline">
      {list.map((step) => (
        <li
          key={step.id}
          className={`transfer-timeline__item ${step.completed ? "is-complete" : ""} ${step.active ? "is-active" : ""}`}
        >
          <div className="transfer-timeline__label">{step.label}</div>
          {step.description ? <p>{step.description}</p> : null}
          {step.date ? <time>{new Date(step.date).toLocaleString()}</time> : null}
        </li>
      ))}
    </ol>
  );
}

export default Timeline;
