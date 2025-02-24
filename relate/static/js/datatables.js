/* eslint-disable func-names */

import './base';
import jQuery from 'jquery';

import datatables from 'datatables.net';

import datatablesBs from 'datatables.net-bs/js/dataTables.bootstrap';
import 'datatables.net-bs/css/dataTables.bootstrap.css';

import datatablesFixedColumns from 'datatables.net-fixedcolumns/js/dataTables.fixedColumns';
import 'datatables.net-fixedcolumns-bs/css/fixedColumns.bootstrap.css';

import * as rlUtils from './rlUtils';

datatables(window, jQuery);
datatablesBs(window, jQuery);
datatablesFixedColumns(window, jQuery);

// {{{ custom sort

function removeTags(s) {
  return s.replace(/(<([^>]+)>)/g, '');
}

jQuery.extend(jQuery.fn.dataTableExt.oSort, {
  'name-asc': function (s1, s2) {
    return removeTags(s1).localeCompare(removeTags(s2));
  },

  'name-desc': function (s1, s2) {
    return removeTags(s2).localeCompare(removeTags(s1));
  },
});

// }}}

/* eslint-disable-next-line import/prefer-default-export */
export { rlUtils };

// vim: foldmethod=marker
