from zope.component.hooks import getSite
from zope.schema.vocabulary import SimpleTerm

from Products.ZCTextIndex.ParseTree import ParseError

from plone.formwidget.contenttree.source import PathSourceBinder, ObjPathSource
from Products.CMFPlone.utils import getToolByName, safe_unicode


class Term(SimpleTerm):
    def __init__(self, value, token=None, title=None, brain=None):
        super(Term, self).__init__(value, token, title)
        self.brain = brain

    @property
    def url(self):
        return self.brain.getURL()

    @property
    def portal_type(self):
        return self.brain.portal_type

    @property
    def extra(self):
        return u""


def parse_query(query, path_prefix=""):
    """Copied from plone.app.vocabularies.catalog.parse_query
    but depth=1 removed.
    """
    query_parts = query.split()
    query = {'SearchableText': []}
    for part in query_parts:
        if part.startswith('path:'):
            path = part[5:]
            query['path'] = {'query': path}
        else:
            query['SearchableText'].append(part)
    text = " ".join(query['SearchableText'])
    for char in '?-+*()':
        text = text.replace(char, ' ')
    query['SearchableText'] = " AND ".join(x + "*" for x in text.split())
    if 'path' in query:
        if query['SearchableText'] == '':
            del query['SearchableText']
#            query["path"]["depth"] = 1
        query["path"]["query"] = path_prefix + query["path"]["query"]
    return query


class ContactSource(ObjPathSource):

    def __init__(self, context, selectable_filter, navigation_tree_query=None):
        super(ContactSource, self).__init__(context, selectable_filter, navigation_tree_query)
        portal_url = getToolByName(getSite(), 'portal_url')
        self.portal_url = portal_url()
        self.portal_path = portal_url.getPortalPath()

    def getTermByBrain(self, brain, real_value=True):
        if real_value:
            value = brain._unrestrictedGetObject()
        else:
            value = brain.getPath()[len(self.portal_path):]
        full_title = safe_unicode(brain.get_full_title or brain.Title or brain.id)
        return Term(value, token=brain.getPath(), title=full_title, brain=brain)

    def tokenToPath(self, token):
        """For token='/Plone/a/b', return '/a/b'
        """
        return token.replace(self.portal_path, '', 1)

    def tokenToUrl(self, token):
        return token.replace(self.portal_path, self.portal_url, 1)

    def search(self, query, limit=20):
        """Copy from plone.formwidget.contenttree.source,
        to be able to use a modified version of parse_query.
        """
        catalog_query = self.selectable_filter.criteria.copy()
        catalog_query.update(parse_query(query, self.portal_path))

        if limit and 'sort_limit' not in catalog_query:
            catalog_query['sort_limit'] = limit

        try:
            results = (self.getTermByBrain(brain, real_value=False)
                       for brain in self.catalog(**catalog_query))
        except ParseError:
            return []

        return results


class ContactSourceBinder(PathSourceBinder):
    path_source = ContactSource
