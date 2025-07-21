class PageGeneratorError(Exception):
    pass


class AsyncDeepseekClientError(PageGeneratorError):
    pass


class UnsplashAsyncClientError(PageGeneratorError):
    pass
