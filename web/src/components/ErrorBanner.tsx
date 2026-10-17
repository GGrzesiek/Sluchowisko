import { ERROR_MESSAGES, type AppError } from "../errors";
import type { LineKind } from "../types";
import { StatusBanner } from "./Chrome";
import { LineBadge } from "./LineBadge";

export function ErrorBanner({ error, lineKind }: { error: AppError; lineKind?: LineKind }) {
  const { title, detail } = ERROR_MESSAGES[error.kind];
  return (
    <div className="flex flex-col gap-3.5">
      <StatusBanner title={title}>{detail}</StatusBanner>
      {error.kind === "positionLost" && error.lastStop && (
        <div className="flex items-center gap-2.5">
          {error.line && (
            <span className="opacity-55">
              <LineBadge line={error.line} kind={lineKind} size="sm" />
            </span>
          )}
          <span className="text-base font-extrabold text-umber">Ostatni znany przystanek: {error.lastStop}</span>
        </div>
      )}
    </div>
  );
}
