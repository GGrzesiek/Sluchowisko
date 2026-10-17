import { fetchRide, RideRequestError } from "./api";

const ride = { vehicle: "3122", line: "22", destination: "Wiatraczna", stops: [{ name: "Okopowa", state: "current" }] };

function answer(status: number, body: unknown) {
  vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify(body), { status }));
}

async function problemOf(promise: Promise<unknown>) {
  const error = await promise.catch((e: unknown) => e);
  expect(error).toBeInstanceOf(RideRequestError);
  return error as RideRequestError;
}

describe("fetchRide", () => {
  it("returns the ride and asks the backend for the vehicle's stops", async () => {
    answer(200, ride);
    await expect(fetchRide("3122")).resolves.toEqual(ride);
    expect(vi.mocked(fetch).mock.calls[0][0]).toMatch(/\/api\/ride\/3122\/stops\/$/);
  });

  it.each([
    [404, { code: "vehicle_not_found" }, "vehicleNotFound"],
    [404, { code: "no_route", line: "999" }, "noRoute"],
    [503, { code: "no_live_data" }, "noLiveData"],
    [502, { code: "city_api" }, "unavailable"],
    [500, "<html>", "unavailable"],
  ])("maps HTTP %i %j to %s", async (status, body, problem) => {
    answer(status, body);
    expect((await problemOf(fetchRide("3122"))).problem).toBe(problem);
  });

  it("keeps the line of a line without stories", async () => {
    answer(404, { code: "no_route", line: "999" });
    expect((await problemOf(fetchRide("1000"))).line).toBe("999");
  });

  it("treats a network failure as unavailable", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    expect((await problemOf(fetchRide("3122"))).problem).toBe("unavailable");
  });

  it("lets a cancelled request stay cancelled", async () => {
    const controller = new AbortController();
    controller.abort();
    vi.mocked(fetch).mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    await expect(fetchRide("3122", controller.signal)).rejects.toHaveProperty("name", "AbortError");
  });
});
