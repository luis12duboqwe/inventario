import type { ReactNode } from "react";

type LogsTableColumn<T> = {
  header: string;
  render: (item: T) => ReactNode;
  key: string;
};

type LogsTableProps<T> = {
  entries: T[];
  columns: Array<LogsTableColumn<T>>;
  emptyMessage: string;
};

function LogsTable<T>({ entries, columns, emptyMessage }: LogsTableProps<T>) {
  if (entries.length === 0) {
    return <p className="muted-text">{emptyMessage}</p>;
  }

  return (
    <div className="table-responsive">
      <table className="outbox-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, index) => (
            <tr key={(entry as { id?: string | number }).id ?? `log-${index}`}>
              {columns.map((column) => (
                <td key={column.key}>{column.render(entry)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export type { LogsTableProps };
export default LogsTable;
