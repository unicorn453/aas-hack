export type AuthStatus =
  | "initializing"
  | "anonymous"
  | "authenticated"
  | "error"
  | "logging-out";

export interface AuthUser {
  username: string;
  displayName: string;
  email?: string;
  roles: string[];
}
