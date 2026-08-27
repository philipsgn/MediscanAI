/**
 * TypeScript Interfaces cho Authentication System (Stage 8).
 * Đồng bộ 100% camelCase wire format với Pydantic Schemas của Backend.
 */

export interface IUser {
  id: string;
  email: string;
  username: string;
  fullName?: string | null;
  createdAt: string;
}

export interface ILoginRequest {
  usernameOrEmail: string;
  password: string;
}

export interface IRegisterRequest {
  email: string;
  username: string;
  password: string;
  fullName?: string;
}

export interface ITokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  user: IUser;
}
