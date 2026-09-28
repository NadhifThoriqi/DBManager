/**
 * api/auth.js — Endpoint grup "Auth"
 * -----------------------------------------------------------------------
 * POST /auth/signin   { user, db, host, port, password }
 * POST /auth/signup   { user, db, host, port, password }
 * POST /auth/logout   (tanpa body)
 *
 * `db` harus salah satu dari: "sqlite" | "mysql" | "postgresql" (lihat
 * schema TypeDB pada openapi.json).
 */

import { post } from './client.js';

/**
 * @param {{user:string, db:string, host:string, port:number, password:string}} payload
 */
export function signIn(payload) {
  return post('/auth/signin', payload);
}

/**
 * @param {{user:string, db:string, host:string, port:number, password:string}} payload
 */
export function signUp(payload) {
  return post('/auth/signup', payload);
}

export function logOut() {
  return post('/auth/logout');
}
