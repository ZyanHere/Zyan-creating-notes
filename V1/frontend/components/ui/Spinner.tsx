// Shown only while a turn is in flight.
//
// Every turn here takes tens of seconds — reading a request, building a plan,
// writing a module. A button that does not move for forty seconds reads as a
// dead one, and the second click is a second model call.

export function Spinner() {
  return (
    <span
      aria-hidden
      className="inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-current border-t-transparent opacity-70"
    />
  );
}
