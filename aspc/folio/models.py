from django.db import models
from django.core.exceptions import FieldError
from django.conf import settings

class Page(models.Model):
    """A glorified static page with Markdown content"""
    
    title = models.CharField(max_length=255, help_text="The page's full title")
    short_title = models.CharField(
        blank=True,
        max_length=80,
        help_text="An optional abbreviated title (for sidebar display)")
    slug = models.CharField(
        help_text="The slug (URL identifier) for the page",
        max_length=80)
    parent = models.ForeignKey(
        'self',
        blank=True,
        null=True,
        help_text="Optional parent page for this one. If none, it is treated"
                  " as a category.")
    summary = models.TextField(
        blank=True,
        null=True,
        help_text="Page summary for display in parent page's"
                  " subpage list (plain text)")
    body = models.TextField(
        blank=True,
        null=True,
        help_text="Page body text written in Markdown")
    sort_order = models.PositiveSmallIntegerField(
        blank=True,
        help_text="Sort ordering")
    stylesheet = models.CharField(
        blank=True,
        null=True,
        max_length=255,
        help_text="Path to an additional stylesheet for this page (relative"
                  " to {0}css/pages/)".format(settings.STATIC_URL))
    visible = models.BooleanField(
        default=True,
        help_text="Determines whether a top or second level page will be "
                  "shown in the sidebar navigation"
    )
    managed = models.BooleanField(
        default=False,
        help_text="Indicates whether this is a special page that should not be "
                  "deleted through normal means. (Don't change this unless "
                  "you know what you're doing!)"
    )
    
    class Meta:
        ordering = ['sort_order', 'title',]
        verbose_name, verbose_name_plural = "page", "pages"

    def __unicode__(self):
        return self.title
    
    def display_title(self):
        if self.short_title:
            return self.short_title
        else:
            return self.title
    
    def get_siblings(self):
        if self.parent:
            return Page.objects.filter(parent=self.parent)
        else:
            return Page.objects.filter(parent__isnull=True)
    
    def path(self):
        path = [self,]
        current = self
        while current.parent:
            path.append(current.parent)
            current = current.parent
        path.reverse()
        return path
    
    def slug_path(self):
        return '/'.join([page.slug for page in self.path()]) + '/'
    
    def save(self, *args, **kwargs):
        self.slug = self.slug.lower()
        if not self.id:
            if self.get_siblings().filter(slug=self.slug).count():
                raise FieldError("Slugs must be unique for a given "
                                 "level in the hierarchy")
        if not self.sort_order:
            if not self.parent:
                pages = Page.objects.filter(parent__isnull=True)
            else:
                pages = self.parent.page_set.all()
            pages = pages.order_by('-sort_order')
            if not pages.count():
                self.sort_order = 1
            else:
                self.sort_order = pages[0].sort_order + 1
        super(Page, self).save(*args, **kwargs)
    
    @models.permalink
    def get_absolute_url(self):
        return ('aspc.folio.views.page_view',
                [],
                {'slug_path': self.slug_path(),})