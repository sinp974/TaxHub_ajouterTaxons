app.directive('createBibnomsListesFormDir', [function () {
  return {
    restrict: 'AE',
    templateUrl:'static/app/components/directives/createBibnomsListesForm-template.html',
    scope : {
      listesDefList:'=',
      listesValues:'='
    },
    link:function($scope, $element, $attrs) {
      myListDir = $scope;
      $scope.listesDefList = $scope.listesDefList || [];
      $scope.listesValues = $scope.listesValues || [];
      //Création de la liste active
      $scope.$watch('listesValues', function(newVal, oldVal) {
        if (! $scope.listesDefList) return;
        refreshListes(newVal);
      }, true);
      $scope.$watch('listesDefList', function(newVal, oldVal) {
        if (newVal) refreshListes($scope.listesValues);
      });

      $scope.removeFromList = function (id_liste) {
        //suppression de l'élément liste
        myListDir.listesValues = myListDir.listesValues.filter(function(a) { return a.id_liste != id_liste });
      };
      $scope.addList = function() {
        //ajout de l'élément liste
        myListDir.listesValues.push(myListDir.selectedList)
      };
      refreshListes = function(newVal) {
        newVal = newVal || [];
        $scope.activeListe = $scope.listesDefList.filter(function(allList){
            return newVal.filter(function(current){
                return allList.id_liste == current.id_liste
            }).length == 0
        });
      }
    }
  }
}]);
