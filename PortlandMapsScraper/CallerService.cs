using NetTopologySuite.Features;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Polly;
using Polly.CircuitBreaker;
using Polly.Retry;
using Polly.Wrap;
using System.Collections.Concurrent;
using System.Data;
using System.Globalization;

namespace PortlandMapsScraper;

/*
Concurrently hit the PortlandMaps api
to scrape historic property assessment
*/ 
internal static class CallerService
{
    private const int _maxConcurrentRequests = 40;
    private const string _apiUri = "https://www.portlandmaps.com/api/detail.cfm";
    private static readonly List<string> _userAgents = new List<string>() {
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0.",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.10 Safari/605.1.1"
    };
    private const int _2022yearsAgo = 3;
    private const int _2018yearsAgo = 7;

    private static readonly HttpClient _httpClient;
    private static readonly SemaphoreSlim _semaphore;
    private static readonly AsyncPolicyWrap<HttpResponseMessage> _policies;

    static CallerService()
    {
        SocketsHttpHandler handler = new SocketsHttpHandler()
        {
            MaxConnectionsPerServer = _maxConcurrentRequests
        };

        _httpClient = new HttpClient(handler);
        _semaphore = new SemaphoreSlim(_maxConcurrentRequests);

        //specify circut breaker policy
        //just incase concurrent requests fail, requiring a break in order to stop socket exhaustion
        AsyncCircuitBreakerPolicy<HttpResponseMessage> circutPolicy = Policy
            .Handle<HttpRequestException>()
            .OrResult<HttpResponseMessage>(response => !response.IsSuccessStatusCode)
            .CircuitBreakerAsync(
                handledEventsAllowedBeforeBreaking: 3,
                durationOfBreak: TimeSpan.FromSeconds(30),
                onBreak: (outcome, b) =>
                {
                    Console.WriteLine("Failed!");
                },
                onReset: () =>
                {
                    Console.WriteLine("Closing");
                },
                onHalfOpen: () =>
                {
                    Console.WriteLine("Half-open");
                });

        //exponential backoff when fail
        AsyncRetryPolicy<HttpResponseMessage> retryPolicy = Policy
            .HandleResult<HttpResponseMessage>(r => !r.IsSuccessStatusCode)
            .Or<HttpRequestException>()
            .WaitAndRetryAsync(10, attempt =>
                TimeSpan.FromSeconds(Math.Pow(2, attempt)));

        _policies = Policy.WrapAsync(circutPolicy, retryPolicy);
    }

    public static async Task<List<Feature>> Call(FeatureCollection _2026dtos)
    {
        ConcurrentBag<Feature> features = new ConcurrentBag<Feature>();
        List<Task> tasks = new List<Task>();

        foreach (Feature dto in _2026dtos)
        {
            tasks.Add(Task.Run(async () =>
            {
                //wait until thread is avaliable
                await _semaphore.WaitAsync();

                try
                {
                    string json = await ApiCall(dto);
                    Feature? feature = ParseThroughResponse(json, dto);

                    if (feature != null)
                    {
                        features.Add(feature);
                    }
                }
                finally
                {
                    //release thread once used
                    _semaphore.Release();
                }
            }));
        }
        await Task.WhenAll(tasks);
        return features.ToList();
    }

    private static async Task<string> ApiCall(Feature dto)
    {
        Random random = new Random();
        string userAgent = _userAgents[random.Next(0, _userAgents.Count)];

        List<KeyValuePair<string, string>> paramsHeader = new List<KeyValuePair<string, string>>()
        {
            new KeyValuePair<string, string>("detail_type", "assessor"),
            new KeyValuePair<string, string>("sections", "*"),
            new KeyValuePair<string, string>("detail_id", $"{dto.Attributes.GetOptionalValue("PRIMACCNUM")}"),
            new KeyValuePair<string, string>("format", "json"),
            //portlandmap devs leaked their api key in the dev interface in their website
            //using it here, I suppose
            new KeyValuePair<string, string>("api_key", "7D700138A0EA40349E799EA216BF82F9")
        };

        HttpResponseMessage response = await _policies.ExecuteAsync(async () =>
        {
            using FormUrlEncodedContent contentHeaders = new FormUrlEncodedContent(paramsHeader);

            using HttpRequestMessage requestMessage = new HttpRequestMessage()
            {
                Method = HttpMethod.Post,
                RequestUri = new Uri(_apiUri),
                Content = contentHeaders
            };
            requestMessage.Headers.Add("User-Agent", userAgent);
            requestMessage.Headers.Add("Referer", "https://portlandmaps.com");
            requestMessage.Headers.Add("X-Requested-With", "XMLHttpRequest");
            requestMessage.Headers.Add("Accept", "application/json, text/plain, */*");

            return await _httpClient.SendAsync(requestMessage);
        });
        return await response.Content.ReadAsStringAsync();
    }

    private static Feature? ParseThroughResponse(string json, Feature _2026dto)
    {
        JObject parsedJson = JObject.Parse(json);

        Geometry? geometry = _2026dto.Geometry;
        if (geometry == null) { return null; }

        double? totalValue2018 = CalcTotalValue(_2018yearsAgo, parsedJson);
        if (totalValue2018 == null) { return null; }
        double? totalValue2022 = CalcTotalValue(_2022yearsAgo, parsedJson);
        if (totalValue2022 == null) { return null; }

        string? stateId = ParseToken<string>("general.parent_state_id", parsedJson);
        if (stateId == null) { return null; }

        return new Feature(
            geometry,
            new AttributesTable(new Dictionary<string, object>
            {
                ["total value (2018)"] = totalValue2018,
                ["total value (2022)"] = totalValue2022,
                ["state id"] = stateId
            }));
    }

    private static double? CalcTotalValue(int yearsAgo, JObject parsedJson)
    {
        string improvements = ParseToken<string>($"$['assessment history'][{yearsAgo}].improvements", parsedJson);
        string land = ParseToken<string>($"$['assessment history'][{yearsAgo}].land", parsedJson);

        //default string type is null
        if (improvements == null || land == null) { return null; }

        return double.Parse(improvements, NumberStyles.AllowCurrencySymbol | NumberStyles.Currency)
            + double.Parse(land, NumberStyles.AllowCurrencySymbol | NumberStyles.Currency);
    }

    private static T ParseToken<T>(string query, JObject parsedJson)
    {
        JToken? token = parsedJson.SelectToken(query);
        if (token == null) return default;
        return token.Value<T>();
    }
}
