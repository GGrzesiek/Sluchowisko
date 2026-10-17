import { act, fireEvent, render, screen } from "@testing-library/react";
import { ErrorStatusProvider, useAppErrors } from "./ErrorStatus";

function PositionLoader() {
  const { report, resolve } = useAppErrors();
  return (
    <>
      <button onClick={() => report({ kind: "positionLost", line: "180", lastStop: "Stare Miasto" })}>zgub</button>
      <button onClick={() => resolve("positionLost")}>znajdź</button>
    </>
  );
}

function Crashing(): never {
  throw new Error("boom");
}

describe("ErrorStatusProvider", () => {
  it("shows no banner while all is well", () => {
    render(<ErrorStatusProvider>ekran</ErrorStatusProvider>);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows the offline banner until the network is back", () => {
    render(<ErrorStatusProvider>ekran</ErrorStatusProvider>);
    act(() => void window.dispatchEvent(new Event("offline")));
    expect(screen.getByRole("status")).toHaveTextContent("Brak internetu");
    act(() => void window.dispatchEvent(new Event("online")));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows an error reported by a screen and hides it once resolved", () => {
    render(
      <ErrorStatusProvider>
        <PositionLoader />
      </ErrorStatusProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "zgub" }));
    expect(screen.getByRole("status")).toHaveTextContent("Łączymy ponownie…");
    expect(screen.getByText("Ostatni znany przystanek: Stare Miasto")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "znajdź" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("replaces a crashed screen with the error banner and a way back to the start", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorStatusProvider>
        <Crashing />
      </ErrorStatusProvider>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Coś poszło nie tak");
    expect(screen.getByRole("button", { name: "Zacznij od nowa" })).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
