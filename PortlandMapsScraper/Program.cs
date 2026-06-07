using NetTopologySuite.IO;
using System.Text;
using Newtonsoft.Json;
using NetTopologySuite.Features;
using PortlandMapsScraper;
using System;

internal static class Program
{
    public static async Task Main(string[] args)
    {
        Console.WriteLine("Deserializing...");
        FeatureCollection _2026dtos = Get2026Dtos();

        Console.WriteLine("Calling API...");
        List<Feature> historicalFeatures = await CallerService.Call(_2026dtos);

        Console.WriteLine("Serializing...");
        await Serialize(historicalFeatures);
    }

    private static FeatureCollection Get2026Dtos()
    {
        string filePath = Path.Combine(Directory.GetCurrentDirectory(), "Resources\\Processed_PortlandLots_2026.geojson");

        using StreamReader streamReader = new StreamReader(filePath, new UTF8Encoding());
        JsonSerializer serializer = GeoJsonSerializer.Create();
        using JsonTextReader textReader = new JsonTextReader(streamReader);

        FeatureCollection dtos = serializer.Deserialize<FeatureCollection>(textReader);
        return dtos;
    }

    private static async Task Serialize(List<Feature> features)
    {
        string outputPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "2021-2022_PortlandTaxlotAssessments.geojson");
        JsonSerializer serializer = GeoJsonSerializer.Create();

        FeatureCollection collection = new FeatureCollection();
        foreach (Feature feature in features)
        {
            collection.Add(feature);
        }

        using StringWriter stringWriter = new StringWriter();
        using JsonTextWriter jsonTextWriter = new JsonTextWriter(stringWriter);

        serializer.Serialize(jsonTextWriter, collection);
        await File.AppendAllTextAsync(outputPath, stringWriter.ToString(), Encoding.UTF8);
        await stringWriter.FlushAsync();

    }
}