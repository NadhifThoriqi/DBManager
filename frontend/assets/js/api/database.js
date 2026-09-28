/**
 * api/database.js — Endpoint grup "Database Management"
 * -----------------------------------------------------------------------
 * POST   /database/create/{engine}   { db_name }
 * GET    /database/show/{engine}     (sqlite: ?search_dir=...)
 * DELETE /database/delete/{engine}   { db_name } (mysql/postgresql juga
 *                                       menerima { user, password } opsional)
 *
 * {engine} = "sqlite" | "mysql" | "postgresql"
 */

import { get, post, del } from './client.js';

const ENGINES = ['sqlite', 'mysql', 'postgresql'];

function assertEngine(engine) {
  if (!ENGINES.includes(engine)) {
    throw new Error(`Engine database tidak dikenal: ${engine}`);
  }
}

/** Membuat database baru pada engine tertentu. */
export function createDatabase(engine, dbName) {
  assertEngine(engine);
  return post(`/database/create/${engine}`, { db_name: dbName });
}

/**
 * Menampilkan daftar database pada engine tertentu.
 * @param {string} engine
 * @param {{searchDir?: string}} [opts] - hanya berlaku untuk sqlite
 * @returns {Promise<{total:number, databases: any[]}>}
 */
export function showDatabases(engine, opts = {}) {
  assertEngine(engine);
  // const params = engine === 'sqlite' && opts.searchDir ? { search_dir: opts.searchDir } : undefined;
  // return get(`/database/show/${engine}`, params);
  return get(`/database/show/${engine}`);
}

/**
 * Menghapus database.
 * @param {string} engine
 * @param {string} dbName
 * @param {{user?: string, password?: string}} [credentials] - hanya dipakai
 *        oleh mysql/postgresql, diabaikan untuk sqlite.
 */
export function deleteDatabase(engine, dbName, credentials = {}) {
  assertEngine(engine);
  const body = { db_name: dbName };
  if (engine !== 'sqlite') {
    if (credentials.user) body.user = credentials.user;
    if (credentials.password) body.password = credentials.password;
  }
  return del(`/database/delete/${engine}`, body);
}

export const DB_ENGINES = ENGINES;
