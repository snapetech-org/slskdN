FROM mcr.microsoft.com/dotnet/aspnet:8.0

WORKDIR /app
COPY --chown=app:app api/bin/Release/net8.0/publish/ ./

RUN mkdir -p /var/slsk/shared /var/slsk/download \
    && chown -R app:app /var/slsk

ENV SLSK_OUTPUT_DIR=/var/slsk/download
ENV SLSK_SHARED_DIR=/var/slsk/shared

ENV ASPNETCORE_URLS=http://+:5000

USER app

ENTRYPOINT ["dotnet", "WebAPI.dll"]
