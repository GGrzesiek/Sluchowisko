import { act, fireEvent, render, screen } from "@testing-library/react";
import { BANNER_VISIBLE_MS, ErrorStatusProvider, useAppErrors } from "./ErrorStatus";

function PositionLoader() {
  const { report, resolve } = useAppErrors();
  return (
    <>
      <button onClick={() => report({ kind: "positionLost", line: "180", lastStop: "Stare Miasto" })}>zgub</button>
      <button onClick={() => report({ kind: "positionLost", line: "180", lastStop: "Muranów" })}>dalej</button>
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

  describe("after a few seconds", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    const renderLoader = () =>
      render(
        <ErrorStatusProvider>
          <PositionLoader />
        </ErrorStatusProvider>,
      );
    const wait = (ms: number) => act(() => vi.advanceTimersByTime(ms));

    it("floats the banner over the screen instead of pushing it down", () => {
      renderLoader();
      fireEvent.click(screen.getByRole("button", { name: "zgub" }));
      expect(screen.getByRole("status").closest(".fixed")).not.toBeNull();
    });

    it("hides the banner by itself", () => {
      renderLoader();
      fireEvent.click(screen.getByRole("button", { name: "zgub" }));
      wait(BANNER_VISIBLE_MS - 1);
      expect(screen.getByRole("status")).toBeInTheDocument();
      wait(1);
      expect(screen.queryByRole("status")).not.toBeInTheDocument();
    });

    it("does not bring back the same problem, but shows it again with new details or after it was fixed", () => {
      renderLoader();
      fireEvent.click(screen.getByRole("button", { name: "zgub" }));
      wait(BANNER_VISIBLE_MS);
      fireEvent.click(screen.getByRole("button", { name: "zgub" }));
      expect(screen.queryByRole("status")).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "dalej" }));
      expect(screen.getByText("Ostatni znany przystanek: Muranów")).toBeInTheDocument();
      wait(BANNER_VISIBLE_MS);

      fireEvent.click(screen.getByRole("button", { name: "znajdź" }));
      fireEvent.click(screen.getByRole("button", { name: "dalej" }));
      expect(screen.getByRole("status")).toHaveTextContent("Łączymy ponownie…");
    });

    it("keeps the banner of a crash, which explains the screen behind it", () => {
      vi.spyOn(console, "error").mockImplementation(() => {});
      render(
        <ErrorStatusProvider>
          <Crashing />
        </ErrorStatusProvider>,
      );
      wait(BANNER_VISIBLE_MS * 2);
      expect(screen.getByRole("status")).toHaveTextContent("Coś poszło nie tak");
    });
  });
});
