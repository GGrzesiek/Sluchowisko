import { act, fireEvent, render, screen } from "@testing-library/react";
import { QrScannerScreen } from "./QrScannerScreen";

const camera = vi.hoisted(() => ({
  start: (): Promise<void> => Promise.resolve(),
  stop: vi.fn(),
  destroy: vi.fn(),
  decode: undefined as undefined | ((result: { data: string }) => void),
}));

vi.mock("qr-scanner", () => ({
  default: vi.fn(function (_video: HTMLVideoElement, onDecode: (result: { data: string }) => void) {
    camera.decode = onDecode;
    return camera;
  }),
}));

function renderScreen() {
  const handlers = { onBack: vi.fn(), onRideFound: vi.fn(), onEnterVehicleNumber: vi.fn() };
  const view = render(<QrScannerScreen {...handlers} />);
  return { ...handlers, ...view };
}

describe("QrScannerScreen", () => {
  beforeEach(() => {
    camera.start = () => Promise.resolve();
  });
  afterEach(() => vi.clearAllMocks());

  it("opens the ride from a sticker code", () => {
    const { onRideFound } = renderScreen();
    act(() => camera.decode?.({ data: "https://ggrzesiek.dev/opendatahackathon42/?line=180&vehicle=1234" }));
    expect(camera.stop).toHaveBeenCalled();
    expect(onRideFound).toHaveBeenCalledWith({ line: "180", vehicle: "1234" });
  });

  it("keeps scanning when the code is not ours", () => {
    const { onRideFound } = renderScreen();
    act(() => camera.decode?.({ data: "https://example.com/menu" }));
    expect(onRideFound).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("To nie jest kod z naszej naklejki");
  });

  it("offers manual entry when the camera is unavailable", async () => {
    camera.start = () => Promise.reject(new DOMException("Permission denied", "NotAllowedError"));
    const { onEnterVehicleNumber } = renderScreen();
    fireEvent.click(await screen.findByRole("button", { name: "Wpisz numer boczny" }));
    expect(screen.getByRole("status")).toHaveTextContent("Nie mamy dostępu do aparatu");
    expect(onEnterVehicleNumber).toHaveBeenCalled();
  });

  it("turns the camera off when leaving the screen", () => {
    const { unmount } = renderScreen();
    unmount();
    expect(camera.destroy).toHaveBeenCalled();
  });
});
