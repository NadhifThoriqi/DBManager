/**
 * api/table.js — Endpoint grup "Table Operations"
 * -----------------------------------------------------------------------
 * POST   /table/list          { db_name }                          -> ListTablesResponse
 * POST   /table/structure     { db_name, table_name }               -> TableStructureResponse
 * POST   /table/content       { db_name, table_name, limit? }       -> TableContentResponse
 * POST   /table/create        { db_name, table_name, columns_def }  -> MessageResponse
 * POST   /table/column/add    { db_name, table_name, column_name, column_type } -> MessageResponse
 * POST   /table/insert        { db_name, table_name, data }         -> MessageResponse
 * PUT    /table/update        { db_name, table_name, update_values, condition_str, condition_params }
 * DELETE /table/row           { db_name, table_name, condition_str, condition_params }
 * DELETE /table/clear         { db_name, table_name }
 * DELETE /table/drop          { db_name, table_name }
 */

import { post, put, del } from './client.js';

/** Nilai valid untuk field `index` pada definisi kolom (schema `Indeks`). */
export const INDEX_TYPES = ['', 'primary', 'unique', 'index', 'fulltext', 'spatial'];

export function listTables(dbName) {
  return post('/table/list', { db_name: dbName });
}

export function getTableStructure(dbName, tableName) {
  return post('/table/structure', { db_name: dbName, table_name: tableName });
}

/**
 * @param {string} dbName
 * @param {string} tableName
 * @param {number} [limit=10] - 1..1000
 */
export function getTableContent(dbName, tableName, limit = 10) {
  return post('/table/content', { db_name: dbName, table_name: tableName, limit });
}

/**
 * @param {string} dbName
 * @param {string} tableName
 * @param {Record<string, {type: string, index?: string}>} columnsDef
 */
export function createTable(dbName, tableName, columnsDef) {
  return post('/table/create', { db_name: dbName, table_name: tableName, columns_def: columnsDef });
}

export function addColumn(dbName, tableName, columnName, columnType) {
  return post('/table/column/add', {
    db_name: dbName,
    table_name: tableName,
    column_name: columnName,
    column_type: columnType,
  });
}

/** @param {Record<string, any>} data - { nama_kolom: nilai } */
export function insertRow(dbName, tableName, data) {
  return post('/table/insert', { db_name: dbName, table_name: tableName, data });
}

/**
 * @param {string} dbName
 * @param {string} tableName
 * @param {Record<string, any>} updateValues
 * @param {string} conditionStr - contoh: "id = :target_id"
 * @param {Record<string, any>} conditionParams - contoh: { target_id: 1 }
 */
export function updateRow(dbName, tableName, updateValues, conditionStr, conditionParams) {
  return put('/table/update', {
    db_name: dbName,
    table_name: tableName,
    update_values: updateValues,
    condition_str: conditionStr,
    condition_params: conditionParams,
  });
}

export function deleteRow(dbName, tableName, conditionStr, conditionParams) {
  return del('/table/row', {
    db_name: dbName,
    table_name: tableName,
    condition_str: conditionStr,
    condition_params: conditionParams,
  });
}

export function clearTable(dbName, tableName) {
  return del('/table/clear', { db_name: dbName, table_name: tableName });
}

export function dropTable(dbName, tableName) {
  return del('/table/drop', { db_name: dbName, table_name: tableName });
}
