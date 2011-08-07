import sys
from pyramid.interfaces import IExceptionViewClassifier
from pyramid.interfaces import IView

from pyramid.events import NewResponse
from zope.interface import providedBy

def excview_tween_factory(handler, registry):
    """ A :term:`tween` factory which produces a tween that catches an
    exception raised by downstream tweens (or the main Pyramid request
    handler) and, if possible, converts it into a Response using an
    :term:`exception view`."""
    has_listeners = registry.has_listeners
    adapters = registry.adapters
    notify = registry.notify

    def excview_tween(request):
        attrs = request.__dict__
        try:
            response = handler(request)
        except Exception, exc:
            # WARNING: do not assign the result of sys.exc_info() to a
            # local var here, doing so will cause a leak
            attrs['exc_info'] = sys.exc_info()
            attrs['exception'] = exc
            # clear old generated request.response, if any; it may
            # have been mutated by the view, and its state is not
            # sane (e.g. caching headers)
            if 'response' in attrs:
                del attrs['response']
            request_iface = attrs['request_iface']
            provides = providedBy(exc)
            for_ = (IExceptionViewClassifier, request_iface.combined, provides)
            view_callable = adapters.lookup(for_, IView, default=None)
            if view_callable is None:
                raise
            response = view_callable(exc, request)
            has_listeners and notify(NewResponse(request, response))
        finally:
            attrs['exc_info'] = None

        return response

    return excview_tween

