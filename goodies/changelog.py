# -*- coding: utf-8 -*-
<%!
from distutils.version import LooseVersion
%>\
## Helper to print items organize by Type and for each type by Severity
<%def name="print_items(items)">\
<% item_by_type = trackers.organize_items_by_field(items, field='Type')%>\
        %for itype in sorted(item_by_type):
<% item_by_severity = trackers.organize_items_by_field(item_by_type[itype], field='Severity')%>\
            %for severity in sorted(item_by_severity):
                %for item in item_by_severity[severity]:
* ${item['Type']}, ${item['Severity']}, ${item[u'Sub System']}, ${item['Composant']}, ${item['summary']}, Found in Release ${item['Found In Release']}, Id[${item['tracker_item_id']}]
                %endfor
            %endfor
        %endfor
</%def>\
\
\
## iterate on trackers
%for t_name in trackers.trackers_name:
## print tracker name
<% title = u"Tracker '" + t_name + "'"%>\
${title}
${"=" * len(title)}

## get tracker by 'fixed in release'
<% item_by_release = trackers.organize_items_by_field(trackers.trackers[t_name]['items'], field='Fixed In Release')%>\
    %for release in sorted(item_by_release, key=LooseVersion, reverse=True):
    %if release != '100': 
<% title = u"Release '" + release + "'"%>\
${title}
${"-" * len(title)}

${print_items(item_by_release[release])}
    %endif
    %endfor
## Print items without 'fixed in release'
    %if '100' in item_by_release: 
<% title = u"Not attached to Release" %>\
${title}
${"-" * len(title)}

<% item_by_resolution = trackers.organize_items_by_field(item_by_release['100'], field='Resolution')%>\
    %for resolution in sorted(item_by_resolution, key=LooseVersion, reverse=True):
<% 
if resolution == '100':
    resolution_t = u"Not Fixed"
else:
    resolution_t = resolution
%>\
${resolution_t}
${"~" * len(resolution_t)}
${print_items(item_by_resolution[resolution])}
    %endfor
    %endif
%endfor
