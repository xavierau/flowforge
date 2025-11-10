# Duplicate API Calls in React 18+ StrictMode

**Date:** 2025-11-03
**Component:** JobList.tsx
**Issue:** Duplicate API calls observed when navigating to /jobs route

## Issue Description

When navigating to `http://localhost:3002/jobs`, the `listJobs()` API was being called twice simultaneously on component mount. This appeared as duplicate network requests in the browser's Network tab.

## Root Cause Analysis

### Primary Cause: React 18+ StrictMode Intentional Behavior

The duplicate calls were caused by **React 18+ StrictMode**, which is enabled in `frontend/src/main.tsx`:

```tsx
// main.tsx lines 7-9
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

**StrictMode in React 18+ intentionally double-invokes effects** in development mode to help developers identify side effects that lack proper cleanup. The lifecycle looks like:

1. Component mounts → `useEffect` runs
2. StrictMode **unmounts** the component → cleanup should run
3. StrictMode **remounts** the component → `useEffect` runs again

This simulates what happens when users navigate away from and back to a page, helping catch bugs related to:
- Missing cleanup functions
- Race conditions in async operations
- Memory leaks from subscriptions/timers

### Secondary Issue: Missing Cleanup Function

The original `useEffect` in JobList.tsx (lines 25-27) had **no cleanup function**:

```tsx
// BEFORE (problematic)
useEffect(() => {
  loadJobs();  // Runs twice in StrictMode
}, []);
```

This could cause **race conditions** where:
1. First API call starts
2. Component unmounts (navigation, StrictMode test)
3. First API call completes and tries to update state → **React warning: "Can't perform state update on unmounted component"**
4. Potential memory leak if not handled

## Solution Implemented

Added a **cleanup flag** to track component mount state and prevent state updates after unmount:

```tsx
// AFTER (fixed) - frontend/src/pages/jobs/JobList.tsx lines 25-57
useEffect(() => {
  let isMounted = true;

  const loadJobs = async () => {
    try {
      setIsLoading(true);
      const response = await listJobs({ limit: 100, offset: 0 });

      // Only update state if component is still mounted
      if (isMounted) {
        setJobs(response.jobs);
      }
    } catch (error) {
      // Only show error if component is still mounted
      if (isMounted) {
        toast.error('Failed to load jobs', {
          description: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    } finally {
      if (isMounted) {
        setIsLoading(false);
      }
    }
  };

  loadJobs();

  // Cleanup function to prevent state updates on unmounted component
  return () => {
    isMounted = false;
  };
}, []);
```

### Why This Fix Works

1. **`isMounted` flag**: Tracks whether the component is still mounted
2. **Cleanup function**: Sets `isMounted = false` when component unmounts
3. **Conditional state updates**: Only updates state if `isMounted === true`
4. **Prevents race conditions**: If the API call completes after unmount, state updates are safely ignored

## Important Notes

### This is EXPECTED Behavior in Development

**The duplicate API calls in development mode are INTENTIONAL and CORRECT.** React StrictMode is working as designed to help you catch bugs. The fix doesn't prevent the duplicate calls in dev mode - it prevents **problems** that could occur from those duplicate calls.

### Production Behavior

In production builds (`npm run build`), StrictMode is typically disabled or has no effect, so:
- The effect will run **only once** on mount
- The cleanup still provides protection against race conditions from user navigation

### When to Use This Pattern

Use the `isMounted` flag pattern whenever you have:
- Async operations (API calls, timers) in useEffect
- State updates that happen after async operations complete
- Risk of component unmounting before async operation finishes

### Alternative: AbortController (More Advanced)

For fetch requests, you can also use `AbortController` to cancel in-flight requests:

```tsx
useEffect(() => {
  const controller = new AbortController();

  const loadJobs = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(url, { signal: controller.signal });
      // ... handle response
    } catch (error) {
      if (error.name !== 'AbortError') {
        // Only handle non-abort errors
      }
    }
  };

  loadJobs();

  return () => {
    controller.abort(); // Cancel in-flight request
  };
}, []);
```

However, our current implementation doesn't expose the raw fetch call, so the `isMounted` flag is the simpler and more appropriate solution.

## Files Modified

- **frontend/src/pages/jobs/JobList.tsx**: Added cleanup function to useEffect (lines 25-57)

## Related Files

- **frontend/src/main.tsx**: StrictMode configuration (lines 1-10)
- **frontend/src/lib/api.ts**: `listJobs()` API function (lines 361-394)
- **frontend/src/App.tsx**: Route configuration (lines 64-73)

## Prevention Strategies

### Best Practices for useEffect with Async Operations

1. **Always include cleanup functions** when performing async operations
2. **Use `isMounted` flag** for simple state update prevention
3. **Use `AbortController`** when you need to cancel in-flight requests
4. **Test in StrictMode** to catch cleanup issues early
5. **Never disable StrictMode** just to hide double-invocation - fix the underlying issue

### Code Review Checklist

When reviewing useEffect hooks:
- [ ] Does it perform async operations?
- [ ] Does it update state after async operations?
- [ ] Does it have a cleanup function?
- [ ] Does cleanup prevent state updates on unmounted components?
- [ ] Does it cancel pending operations (timers, requests) on cleanup?

## References

- [React 18 StrictMode Behavior](https://react.dev/reference/react/StrictMode)
- [useEffect Cleanup Pattern](https://react.dev/learn/synchronizing-with-effects#fetching-data)
- [Fixing Race Conditions](https://react.dev/learn/you-might-not-need-an-effect#fetching-data)

## Verification

To verify the fix works correctly:

1. **Development mode** (with StrictMode):
   ```bash
   cd frontend
   npm run dev
   ```
   - Navigate to http://localhost:3002/jobs
   - Open DevTools → Network tab
   - You will still see 2 API calls (expected in dev)
   - No React warnings in console about state updates

2. **Production mode** (StrictMode disabled):
   ```bash
   cd frontend
   npm run build
   npm run preview
   ```
   - Navigate to the jobs page
   - Should see only 1 API call
   - Component works correctly

3. **Test unmount scenario**:
   - Navigate to /jobs (starts loading)
   - Immediately navigate away before loading completes
   - No console errors should appear
   - No memory leaks or state update warnings

## Conclusion

The "duplicate API calls" were not a bug but **expected StrictMode behavior** designed to help identify missing cleanup functions. The fix ensures the component handles unmounting gracefully, preventing potential race conditions and state update warnings in both development and production environments.

**Key Takeaway**: StrictMode double-mounting is a feature, not a bug. Always implement proper cleanup functions for side effects.
