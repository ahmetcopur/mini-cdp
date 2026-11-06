// Returns a function that runs fn only once it has not been called again for `ms`
// milliseconds, so typing sends one request instead of one per keystroke.
export function debounce(fn, ms = 300) {
  let timer;
  const debounced = () => {
    clearTimeout(timer);
    timer = setTimeout(fn, ms);
  };
  debounced.cancel = () => clearTimeout(timer);
  return debounced;
}
