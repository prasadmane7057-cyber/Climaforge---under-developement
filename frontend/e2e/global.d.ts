export {};

declare global {
  interface Window {
    __CLIMAFORGE_AUTH__: {
      getAccessToken: () => string | null;
      setAccessToken: (token: string | null) => void;
      clearAccessToken: () => void;
      refreshAccessToken: () => Promise<string | null>;
      loginUser: (email: string, pass: string) => Promise<{ token: string }>;
      logoutUser: () => Promise<void>;
      fetchCurrentUser: () => Promise<unknown>;
      restoreSession: () => Promise<unknown>;
    };
    __CLIMAFORGE_AUTHSYNC__: {
      isWebLocksSupported: () => boolean;
      isBroadcastChannelSupported: () => boolean;
      executeWithRefreshLock: <T>(action: () => Promise<T>) => Promise<T>;
      clearCrossTabState: () => void;
      broadcastAuthEvent: (msg: unknown) => void;
      onAuthBroadcast: (listener: unknown) => () => void;
      recordRefreshCompletedCrossTab: () => void;
      recordLogoutCrossTab: () => void;
      recordSessionExpiredCrossTab: () => void;
      recordLoginCrossTab: () => void;
      isRecentRefreshCompleted: () => boolean;
      isRecentCrossTabSessionExpired: () => boolean;
    };
  }
}

